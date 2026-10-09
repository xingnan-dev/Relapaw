import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const pet = { id: 7, name: "Mochi", species: "cat", breed: null, birth_date: null, approximate_age: null, sex: null, neutered: null, created_at: "2026-01-01T00:00:00Z" };

function json(data: unknown, ok = true, status = ok ? 200 : 500) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(data) });
}

function mockApi(options: { pets?: typeof pet[]; storedPetValid?: boolean; storedPetUnavailable?: boolean; timeline?: unknown; completeError?: boolean } = {}) {
  const pets = options.pets ?? [];
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/v1/pets" && init?.method === "POST") return json(pet);
    if (url === "/api/v1/episodes/complete" && init?.method === "POST") return options.completeError ? json({ error: { code: "INTERNAL_ERROR", message: "Failed" } }, false, 500) : json({ id: 11 }, true, 201);
    if (url === "/api/v1/pets") return json(pets);
    if (url === "/api/v1/pets/7") {
      if (options.storedPetUnavailable) return json({}, false, 503);
      return options.storedPetValid === false ? json({}, false, 404) : json(pet);
    }
    if (url.startsWith("/api/v1/pets/7/follow-ups")) return json([]);
    if (url.startsWith("/api/v1/pets/7/timeline")) return json(options.timeline ?? { items: [], total: 0, page: 1, page_size: 20, has_more: false });
    if (url.startsWith("/api/v1/episodes/") && !init?.method) {
      const item = (options.timeline as { items?: unknown[] } | undefined)?.items?.[0];
      return item ? json(item) : json({ error: { code: "EPISODE_NOT_FOUND", message: "Episode not found" } }, false, 404);
    }
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
    expect(await screen.findByText("发生了什么")).toBeInTheDocument();
    expect(screen.getByText("你的理解")).toBeInTheDocument();
  });

  it("does not depend on motion to navigate", async () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
    render(<App />);
    await screen.findByRole("heading", { name: "Mochi" });
    fireEvent.click(screen.getByRole("button", { name: "Understand" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "它怎么啦？" })).toBeInTheDocument());
  });

  it("validates the two lenses before saving", async () => {
    const fetchMock = mockApi({ pets: [pet] });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await screen.findByRole("heading", { name: "Mochi" });
    fireEvent.click(screen.getByRole("button", { name: "Understand" }));
    fireEvent.click(screen.getByRole("button", { name: "保存手工记录" }));
    expect(screen.getByRole("alert")).toHaveTextContent("请填写原始描述和至少一条客观观察");
    expect(fetchMock.mock.calls.some(([input]) => String(input) === "/api/v1/episodes/complete")).toBe(false);
  });

  it("saves a complete manual record and opens Timeline", async () => {
    const fetchMock = mockApi({ pets: [pet] });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await screen.findByRole("heading", { name: "Mochi" });
    fireEvent.click(screen.getByRole("button", { name: "Understand" }));
    fireEvent.change(screen.getByLabelText("原始描述"), { target: { value: "她躲到沙发后，我觉得她紧张。" } });
    fireEvent.change(screen.getByLabelText("发生了什么"), { target: { value: "她在沙发后停留了 20 分钟。" } });
    fireEvent.change(screen.getByLabelText("你的理解"), { target: { value: "我觉得访客让她紧张。" } });
    fireEvent.change(screen.getByLabelText("地点"), { target: { value: "客厅" } });
    fireEvent.click(screen.getByRole("button", { name: "保存手工记录" }));

    expect(await screen.findByRole("heading", { name: "长期记录" })).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([input]) => String(input) === "/api/v1/episodes/complete");
    const payload = JSON.parse(String(call?.[1]?.body));
    expect(payload.pet_id).toBe(7);
    expect(payload.observations[0].description).toContain("20 分钟");
    expect(payload.owner_interpretations[0].interpretation).toContain("访客");
    expect(payload.safety_check.result).toBe("NORMAL");
  });

  it("shows a persistent veterinary warning and submits only user-selected signals", async () => {
    const fetchMock = mockApi({ pets: [pet] });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await screen.findByRole("heading", { name: "Mochi" });
    fireEvent.click(screen.getByRole("button", { name: "Understand" }));
    fireEvent.change(screen.getByLabelText("原始描述"), { target: { value: "呼吸看起来很困难。" } });
    fireEvent.change(screen.getByLabelText("发生了什么"), { target: { value: "张口呼吸，胸部起伏明显。" } });
    fireEvent.click(screen.getByLabelText("存在需要尽快联系兽医的情况"));
    expect(screen.getByRole("alert")).toHaveTextContent("请尽快联系兽医");
    fireEvent.click(screen.getByLabelText("呼吸困难"));
    fireEvent.click(screen.getByRole("button", { name: "保存手工记录" }));

    await screen.findByRole("heading", { name: "长期记录" });
    const call = fetchMock.mock.calls.find(([input]) => String(input) === "/api/v1/episodes/complete");
    const payload = JSON.parse(String(call?.[1]?.body));
    expect(payload.safety_check).toMatchObject({ result: "ESCALATE_TO_VET", danger_signals: ["breathing_difficulty"] });
  });

  it("keeps the draft after a failed save and allows retry", async () => {
    const base = mockApi({ pets: [pet] });
    let attempts = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/v1/episodes/complete") {
        attempts += 1;
        return attempts === 1 ? json({ error: { code: "INTERNAL_ERROR", message: "Failed" } }, false, 500) : json({ id: 12 }, true, 201);
      }
      return base(input, init);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await screen.findByRole("heading", { name: "Mochi" });
    fireEvent.click(screen.getByRole("button", { name: "Understand" }));
    fireEvent.change(screen.getByLabelText("原始描述"), { target: { value: "需要保留的草稿" } });
    fireEvent.change(screen.getByLabelText("发生了什么"), { target: { value: "连续走动五分钟" } });
    fireEvent.click(screen.getByRole("button", { name: "保存手工记录" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("输入仍保留");
    expect(screen.getByLabelText("原始描述")).toHaveValue("需要保留的草稿");
    fireEvent.click(screen.getByRole("button", { name: "保存手工记录" }));
    expect(await screen.findByRole("heading", { name: "长期记录" })).toBeInTheDocument();
    expect(attempts).toBe(2);
  });
});

const managedEpisode = {
  id: 21, pet_id: 7, happened_at: "2026-10-08T01:30:00Z", episode_type: "behavior_change",
  raw_owner_input: "她躲到沙发后。", context: { weather: "rain" }, duration_seconds: 1200,
  frequency_count: 1, intensity: 2, location: "客厅", trigger_context: "访客到达",
  created_at: "2026-10-08T01:35:00Z", updated_at: "2026-10-08T01:35:00Z",
  observations: [{ id: 31, episode_id: 21, behavior_type: "hiding", description: "在沙发后停留 20 分钟", source_type: "owner_direct", confidence: null, measured_value: 20, unit: "minutes", created_at: "2026-10-08T01:35:00Z", updated_at: "2026-10-08T01:35:00Z" }],
  owner_interpretations: [{ id: 41, episode_id: 21, interpretation: "我觉得访客让她紧张", created_at: "2026-10-08T01:35:00Z", updated_at: "2026-10-08T01:35:00Z" }],
  safety_check: { id: 51, episode_id: 21, result: "NORMAL", danger_signals: [], other_concern: null, acknowledged_at: "2026-10-08T01:35:00Z", created_at: "2026-10-08T01:35:00Z" },
  evidence_references: [{ id: 61, episode_id: 21, source_type: "RAW_OWNER_INPUT", source_id: 21, field_path: "raw_owner_input", observed_at: "2026-10-08T01:30:00Z", recorded_at: "2026-10-08T01:35:00Z", created_at: "2026-10-08T01:35:00Z" }],
  plan_links: [], veterinary_escalations: [],
};

function timelineApi(handler?: (url: string, init?: RequestInit) => Promise<unknown> | undefined) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const custom = handler?.(url, init);
    if (custom) return custom;
    if (url === "/api/v1/pets") return json([pet]);
    if (url.startsWith("/api/v1/pets/7/follow-ups")) return json([]);
    if (url === "/api/v1/episodes/21") return json(managedEpisode);
    if (url.startsWith("/api/v1/pets/7/timeline")) return json({ items: [managedEpisode], total: 1, page: 1, page_size: 20, has_more: false });
    return json({}, false, 404);
  });
}

async function openManagedTimeline(fetchMock = timelineApi()) {
  localStorage.setItem("relapaw.onboarding.completed", "true");
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await screen.findByRole("heading", { name: "Mochi" });
  fireEvent.click(screen.getByRole("button", { name: "Timeline" }));
  await screen.findByText("她躲到沙发后。");
  return fetchMock;
}

describe("timeline management", () => {
  it("sends time and type filters", async () => {
    const fetchMock = await openManagedTimeline();
    fireEvent.click(screen.getByRole("button", { name: "7 天" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).includes("from=") && String(input).includes("to="))).toBe(true));
    fireEvent.change(screen.getByLabelText("记录类型筛选"), { target: { value: "feeding" } });
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).includes("episode_type=feeding"))).toBe(true));
  });

  it("loads full detail and keeps both lenses and safety separate", async () => {
    await openManagedTimeline();
    fireEvent.click(screen.getByRole("button", { name: /behavior_change/ }));
    expect(await screen.findByRole("heading", { name: "记录详情" })).toBeInTheDocument();
    expect(screen.getByText("原始输入")).toBeInTheDocument();
    expect(screen.getByText("发生了什么")).toBeInTheDocument();
    expect(screen.getByText("你的理解")).toBeInTheDocument();
    expect(screen.getByText("人工 Safety Check")).toBeInTheDocument();
    expect(screen.getByText("Evidence 来源信息")).toBeInTheDocument();
  });

  it("validates edits and saves separated fields", async () => {
    const changed = { ...managedEpisode, raw_owner_input: "更新后的原始输入" };
    const fetchMock = await openManagedTimeline(timelineApi((url, init) => url === "/api/v1/episodes/21" && init?.method === "PUT" ? json(changed) : undefined));
    fireEvent.click(screen.getByRole("button", { name: /behavior_change/ }));
    await screen.findByRole("heading", { name: "记录详情" });
    fireEvent.click(screen.getByRole("button", { name: "编辑记录" }));
    fireEvent.change(screen.getByLabelText("Observation"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Observation");
    fireEvent.change(screen.getByLabelText("Observation"), { target: { value: "走进厨房" } });
    fireEvent.change(screen.getByLabelText("原始输入"), { target: { value: "更新后的原始输入" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));
    expect(await screen.findByRole("heading", { name: "记录详情" })).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([input, init]) => String(input) === "/api/v1/episodes/21" && init?.method === "PUT");
    const body = JSON.parse(String(call?.[1]?.body));
    expect(body.observations[0].description).toBe("走进厨房");
    expect(body.owner_interpretations[0].interpretation).toContain("访客");
    expect(body.pet_id).toBeUndefined();
  });

  it("preserves an edit after a network failure and permits retry", async () => {
    let attempts = 0;
    await openManagedTimeline(timelineApi((url, init) => {
      if (url === "/api/v1/episodes/21" && init?.method === "PUT") { attempts += 1; return attempts === 1 ? json({}, false, 503) : json({ ...managedEpisode, raw_owner_input: "保留的编辑" }); }
      return undefined;
    }));
    fireEvent.click(screen.getByRole("button", { name: /behavior_change/ })); await screen.findByRole("heading", { name: "记录详情" });
    fireEvent.click(screen.getByRole("button", { name: "编辑记录" }));
    fireEvent.change(screen.getByLabelText("原始输入"), { target: { value: "保留的编辑" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("输入仍保留");
    expect(screen.getByLabelText("原始输入")).toHaveValue("保留的编辑");
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));
    expect(await screen.findByRole("heading", { name: "记录详情" })).toBeInTheDocument();
    expect(attempts).toBe(2);
  });

  it("requires confirmation, supports cancel, and removes a deleted row", async () => {
    let deleted = false;
    const fetchMock = await openManagedTimeline(timelineApi((url, init) => {
      if (url === "/api/v1/episodes/21" && init?.method === "DELETE") { deleted = true; return Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(undefined) }); }
      if (deleted && url.startsWith("/api/v1/pets/7/timeline")) return json({ items: [], total: 0, page: 1, page_size: 20, has_more: false });
      return undefined;
    }));
    fireEvent.click(screen.getByRole("button", { name: /behavior_change/ })); await screen.findByRole("heading", { name: "记录详情" });
    fireEvent.click(screen.getByRole("button", { name: "删除记录" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Evidence");
    fireEvent.click(screen.getByRole("button", { name: "取消删除" }));
    expect(screen.getByRole("heading", { name: "记录详情" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "删除记录" }));
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));
    expect(await screen.findByText("当前筛选下还没有事件记录。")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input, init]) => String(input) === "/api/v1/episodes/21" && init?.method === "DELETE")).toBe(true);
  });

  it("keeps a persistent veterinary escalation warning", async () => {
    const urgent = { ...managedEpisode, safety_check: { ...managedEpisode.safety_check, result: "ESCALATE_TO_VET", danger_signals: ["breathing_difficulty"] }, veterinary_escalations: [{ id: 70, episode_id: 21, reason: "breathing_difficulty", status: "OPEN", vet_brief: null }] };
    await openManagedTimeline(timelineApi((url) => url === "/api/v1/episodes/21" ? json(urgent) : undefined));
    fireEvent.click(screen.getByRole("button", { name: /behavior_change/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Relapaw 不进行诊断，也不替代兽医");
  });

  it("manually advances and closes a veterinary escalation", async () => {
    let status = "OPEN";
    const urgent = () => ({ ...managedEpisode, safety_check: { ...managedEpisode.safety_check, result: "ESCALATE_TO_VET", danger_signals: ["breathing_difficulty"] }, veterinary_escalations: [{ id: 70, episode_id: 21, reason: "breathing_difficulty", status, vet_brief: null }] });
    const fetchMock = await openManagedTimeline(timelineApi((url, init) => {
      if (url === "/api/v1/episodes/21") return json(urgent());
      if (url === "/api/v1/veterinary-escalations/70" && init?.method === "PATCH") { status = JSON.parse(String(init.body)).status; return json(urgent().veterinary_escalations[0]); }
      return undefined;
    }));
    fireEvent.click(screen.getByRole("button", { name: /behavior_change/ }));
    expect(await screen.findByRole("button", { name: "标记已分享给兽医" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "标记已分享给兽医" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("SHARED_WITH_VET"));
    expect(screen.queryByRole("button", { name: "标记已分享给兽医" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "关闭升级" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("CLOSED"));
    expect(screen.queryByRole("button", { name: "关闭升级" })).not.toBeInTheDocument();
    const statuses = fetchMock.mock.calls.filter(([input, init]) => String(input) === "/api/v1/veterinary-escalations/70" && init?.method === "PATCH").map(([, init]) => JSON.parse(String(init?.body)).status);
    expect(statuses).toEqual(["SHARED_WITH_VET", "CLOSED"]);
  });

  it("keeps the veterinary escalation state visible when an update fails", async () => {
    const urgent = { ...managedEpisode, veterinary_escalations: [{ id: 70, episode_id: 21, reason: "breathing_difficulty", status: "OPEN", vet_brief: null }] };
    await openManagedTimeline(timelineApi((url, init) => {
      if (url === "/api/v1/episodes/21") return json(urgent);
      if (url === "/api/v1/veterinary-escalations/70" && init?.method === "PATCH") return json({}, false, 503);
      return undefined;
    }));
    fireEvent.click(screen.getByRole("button", { name: /behavior_change/ }));
    fireEvent.click(await screen.findByRole("button", { name: "关闭升级" }));
    expect(await screen.findByText("更新兽医升级状态失败，原状态仍然保留。请重试。")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("OPEN");
    expect(screen.getByRole("button", { name: "关闭升级" })).toBeInTheDocument();
  });

  it("shows delete failure and list loading failure with retry", async () => {
    let listAttempts = 0;
    const fetchMock = timelineApi((url, init) => {
      if (url.startsWith("/api/v1/pets/7/timeline")) { listAttempts += 1; return listAttempts === 1 ? json({}, false, 503) : json({ items: [managedEpisode], total: 1, page: 1, page_size: 20, has_more: false }); }
      if (url === "/api/v1/episodes/21" && init?.method === "DELETE") return json({}, false, 503);
      return undefined;
    });
    localStorage.setItem("relapaw.onboarding.completed", "true"); vi.stubGlobal("fetch", fetchMock); render(<App />);
    await screen.findByRole("heading", { name: "Mochi" }); fireEvent.click(screen.getByRole("button", { name: "Timeline" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("暂时无法读取 Timeline");
    fireEvent.click(screen.getByRole("button", { name: "重试" })); await screen.findByText("她躲到沙发后。");
    fireEvent.click(screen.getByRole("button", { name: /behavior_change/ })); await screen.findByRole("heading", { name: "记录详情" });
    fireEvent.click(screen.getByRole("button", { name: "删除记录" })); fireEvent.click(screen.getByRole("button", { name: "确认删除" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("记录仍然保留");
  });
});

const dueFollowUp = { id: 81, source_episode_id: 21, result_episode_id: null, scheduled_at: "2026-10-08T01:30:00Z", status: "PENDING", outcome: null, created_at: "2026-10-07T01:30:00Z", completed_at: null, source_episode_type: "behavior_change", source_raw_owner_input: "她躲到沙发后。", source_happened_at: "2026-10-07T01:00:00Z", timing_status: "DUE" };
const overdueFollowUp = { ...dueFollowUp, id: 82, source_raw_owner_input: "昨天的记录", timing_status: "OVERDUE" };

async function openTodayWith(fetchMock: ReturnType<typeof vi.fn>) {
  localStorage.setItem("relapaw.onboarding.completed", "true"); vi.stubGlobal("fetch", fetchMock); render(<App />);
  await screen.findByRole("heading", { name: "Mochi" });
}

describe("follow-up flow", () => {
  it("shows honest empty state and retries a failed Today request", async () => {
    let attempts = 0;
    const fetchMock = timelineApi((url) => {
      if (url.startsWith("/api/v1/pets/7/follow-ups")) { attempts += 1; return attempts === 1 ? json({}, false, 503) : json([]); }
      return undefined;
    });
    await openTodayWith(fetchMock);
    expect(await screen.findByRole("alert")).toHaveTextContent("暂时无法读取待复评项目");
    fireEvent.click(screen.getByRole("button", { name: "重试待复评" }));
    expect(await screen.findByText("目前没有到期或逾期的复评。")).toBeInTheDocument();
  });

  it("shows due and overdue items and supports cancel confirmation", async () => {
    let cancelled = false;
    const fetchMock = timelineApi((url, init) => {
      if (url.startsWith("/api/v1/pets/7/follow-ups")) return json(cancelled ? [dueFollowUp] : [dueFollowUp, overdueFollowUp]);
      if (url === "/api/v1/follow-ups/82/cancel" && init?.method === "POST") { cancelled = true; return json({ ...overdueFollowUp, status: "CANCELLED" }); }
      return undefined;
    });
    await openTodayWith(fetchMock);
    expect(await screen.findByText("今日到期")).toBeInTheDocument();
    expect(screen.getByText("已逾期")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "取消复评" })[1]);
    expect(screen.getByRole("dialog")).toHaveTextContent("原 Episode 保持不变");
    fireEvent.click(screen.getByRole("button", { name: "返回" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "取消复评" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "确认取消复评" }));
    await waitFor(() => expect(screen.queryByText("昨天的记录")).not.toBeInTheDocument());
  });

  it("completes a follow-up with separated lenses, persistent safety, and opens the result", async () => {
    const resultEpisode = { ...managedEpisode, id: 22, raw_owner_input: "复评后的原始输入", result_of_follow_up: { ...dueFollowUp, result_episode_id: 22, status: "COMPLETED", outcome: "WORSENED" }, scheduled_follow_ups: [] };
    const fetchMock = timelineApi((url, init) => {
      if (url.startsWith("/api/v1/pets/7/follow-ups")) return json([dueFollowUp]);
      if (url === "/api/v1/follow-ups/81/complete" && init?.method === "POST") return json(resultEpisode);
      if (url === "/api/v1/episodes/22") return json(resultEpisode);
      return undefined;
    });
    await openTodayWith(fetchMock);
    fireEvent.click(await screen.findByRole("button", { name: "开始复评" }));
    expect(screen.getByText("发生了什么（Observation）")).toBeInTheDocument();
    expect(screen.getByText("你的理解（Owner Interpretation）")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("复评原始输入"), { target: { value: "复评后的原始输入" } });
    fireEvent.change(screen.getByLabelText("复评 Observation"), { target: { value: "仍在沙发后停留" } });
    fireEvent.change(screen.getByLabelText("复评 Owner Interpretation"), { target: { value: "我觉得情况加重" } });
    fireEvent.click(screen.getByLabelText("存在需要尽快联系兽医的情况"));
    expect(screen.getByRole("alert")).toHaveTextContent("Relapaw 不进行诊断，也不替代兽医");
    fireEvent.click(screen.getByLabelText("呼吸困难"));
    fireEvent.click(screen.getByLabelText("加重"));
    fireEvent.click(screen.getByRole("button", { name: "保存复评" }));
    expect(await screen.findByRole("heading", { name: "记录详情" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看原记录" })).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([input, init]) => String(input) === "/api/v1/follow-ups/81/complete" && init?.method === "POST");
    const body = JSON.parse(String(call?.[1]?.body));
    expect(body.outcome).toBe("WORSENED"); expect(body.observations[0].description).toContain("沙发后"); expect(body.owner_interpretations[0].interpretation).toContain("加重");
  });

  it("preserves the completion draft after network failure and retries", async () => {
    let attempts = 0;
    const fetchMock = timelineApi((url, init) => {
      if (url.startsWith("/api/v1/pets/7/follow-ups")) return json([dueFollowUp]);
      if (url === "/api/v1/follow-ups/81/complete" && init?.method === "POST") { attempts += 1; return attempts === 1 ? json({}, false, 503) : json({ ...managedEpisode, id: 22 }); }
      if (url === "/api/v1/episodes/22") return json({ ...managedEpisode, id: 22 });
      return undefined;
    });
    await openTodayWith(fetchMock); fireEvent.click(await screen.findByRole("button", { name: "开始复评" }));
    fireEvent.change(screen.getByLabelText("复评原始输入"), { target: { value: "需要保留" } }); fireEvent.change(screen.getByLabelText("复评 Observation"), { target: { value: "客观记录" } });
    fireEvent.click(screen.getByRole("button", { name: "保存复评" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("输入仍保留"); expect(screen.getByLabelText("复评原始输入")).toHaveValue("需要保留");
    fireEvent.click(screen.getByRole("button", { name: "保存复评" })); await screen.findByRole("heading", { name: "记录详情" }); expect(attempts).toBe(2);
  });

  it("offers all scheduling presets and validates custom time", async () => {
    const fetchMock = await openManagedTimeline(timelineApi((url, init) => url === "/api/v1/episodes/21/follow-ups" && init?.method === "POST" ? json({ ...dueFollowUp, scheduled_at: JSON.parse(String(init.body)).scheduled_at }) : undefined));
    fireEvent.click(screen.getByRole("button", { name: /behavior_change/ })); await screen.findByRole("heading", { name: "记录详情" }); fireEvent.click(screen.getByRole("button", { name: "安排复评" }));
    expect(screen.getByRole("button", { name: "2 小时后" })).toBeInTheDocument(); expect(screen.getByRole("button", { name: "次日" })).toBeInTheDocument(); expect(screen.getByRole("button", { name: "3 天后" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "2 小时后" })); fireEvent.click(screen.getByRole("button", { name: "次日" })); fireEvent.click(screen.getByRole("button", { name: "3 天后" }));
    fireEvent.change(screen.getByLabelText("自定义复评时间"), { target: { value: "2020-01-01T00:00" } }); fireEvent.click(screen.getByRole("button", { name: "确认安排" })); expect(screen.getByRole("alert")).toHaveTextContent("当前时间之后");
    fireEvent.change(screen.getByLabelText("自定义复评时间"), { target: { value: "2099-01-01T12:00" } }); fireEvent.click(screen.getByRole("button", { name: "确认安排" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([input, init]) => String(input) === "/api/v1/episodes/21/follow-ups" && init?.method === "POST")).toBe(true));
  });
});

describe("observation plan flow", () => {
  const plan = { id: 91, pet_id: 7, status: "ACTIVE", start_at: "2026-10-08T00:00:00Z", end_at: "2026-10-15T00:00:00Z", goal: "观察门口停留", items_to_observe: [], items: [{ id: 1, plan_id: 91, label: "记录停留秒数", description: null, sort_order: 0, is_required: true, created_at: "2026-10-08T00:00:00Z" }] };

  it("creates, displays, completes and cancels plans", async () => {
    let plans: unknown[] = [];
    const fetchMock = timelineApi((url, init) => {
      if (url === "/api/v1/pets/7/observation-plans" && init?.method === "POST") { plans = [plan]; return json(plan, true, 201); }
      if (url === "/api/v1/pets/7/observation-plans") return json(plans);
      if (url === "/api/v1/observation-plans/91" && init?.method === "PATCH") { plans = []; return json({ ...plan, status: JSON.parse(String(init.body)).status }); }
      return undefined;
    });
    await openTodayWith(fetchMock); fireEvent.click(await screen.findByRole("button", { name: "创建观察计划" }));
    fireEvent.change(screen.getByLabelText("观察目标"), { target: { value: "观察门口停留" } }); fireEvent.change(screen.getByLabelText("观察项目"), { target: { value: "记录停留秒数" } }); fireEvent.click(screen.getByRole("button", { name: "保存计划" }));
    expect(await screen.findByText("记录停留秒数")).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: "取消计划" })); expect(screen.getByRole("dialog")).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: "返回" }));
    fireEvent.click(screen.getByRole("button", { name: "完成计划" })); await screen.findByText("暂无进行中的观察计划。");
  });

  it("offers active plans when saving an observation", async () => {
    const fetchMock = timelineApi((url) => url === "/api/v1/pets/7/observation-plans" ? json([plan]) : undefined);
    await openTodayWith(fetchMock); fireEvent.click(screen.getByRole("button", { name: "Understand" }));
    expect(await screen.findByRole("option", { name: "观察门口停留" })).toBeInTheDocument();
  });
});
