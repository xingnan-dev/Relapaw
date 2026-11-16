import { expect, test, type Locator, type Page } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

test.use({ timezoneId: "Asia/Shanghai" });

async function login(page: Page, email: string) {
  await page.goto("/");
  await page.getByLabel("受邀邮箱").fill(email);
  await page.getByRole("button", { name: "获取验证码" }).click();
  await page.getByLabel("一次性验证码").fill("246810");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.getByRole("heading", { name: "开始前，请确认数据约定" }).waitFor();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "接受并继续" }).click();
  await page.getByRole("button", { name: "翻到下一页" }).click();
  await page.getByRole("button", { name: "翻到下一页" }).click();
  await page.getByRole("button", { name: "开始建立档案" }).click();
}

async function createPet(page: Page, name: string) {
  await page.getByLabel("名字", { exact: true }).fill(name);
  await page.getByLabel("物种", { exact: true }).fill("猫");
  await page.getByRole("button", { name: "继续补充一点" }).click();
  const saved = page.waitForResponse((response) =>
    response.url().endsWith("/api/v1/pets") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "完成建档" }).click();
  const pet = await (await saved).json() as { id: number };
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  const opening = page.getByRole("button", { name: /和它一起开始/ });
  try {
    await opening.waitFor({ state: "visible", timeout: 1500 });
    await opening.click();
  } catch { /* already dismissed for this account */ }
  return pet;
}

async function createRecord(page: Page, raw: string) {
  await page.getByRole("button", { name: "Understand" }).click();
  await page.getByLabel("原始描述").fill(raw);
  const saved = page.waitForResponse((response) =>
    response.url().endsWith("/api/v1/episodes/complete") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "保存这条记录" }).click();
  const episode = await (await saved).json() as { id: number };
  await expect(page.getByRole("heading", { name: "记录详情" })).toBeVisible();
  return episode;
}

async function schedule(page: Page) {
  await page.getByRole("button", { name: "安排复评" }).click();
  await page.getByRole("button", { name: "次日" }).click();
  const saved = page.waitForResponse((response) =>
    /\/episodes\/\d+\/follow-ups$/.test(response.url()) && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "确认安排" }).click();
  const followUp = await (await saved).json() as { id: number; source_episode_id: number };
  await expect(page.getByRole("heading", { name: "记录详情" })).toBeVisible();
  return followUp;
}

// Only change scheduling in the exact disposable DB owned by this Playwright run.
async function setTestDueTime(page: Page, followUp: { id: number; source_episode_id: number }, date: Date) {
  const backend = resolve(import.meta.dirname, "..", "..", "backend");
  const manifest = JSON.parse(readFileSync(resolve(backend, ".e2e", "server-pids.json"), "utf8"));
  const ready = await (await page.request.get("/ready")).json();
  expect(ready.deployment_version).toBe(manifest.runId);
  const result = spawnSync(resolve(backend, ".venv", "Scripts", "python.exe"), [
    "-c",
    "import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); " +
    "changed=db.execute(\"UPDATE episode_follow_ups SET scheduled_at=? WHERE id=? AND source_episode_id=? AND status='PENDING'\", (sys.argv[4],int(sys.argv[2]),int(sys.argv[3]))).rowcount; " +
    "db.commit(); db.close(); assert changed == 1",
    resolve(backend, ".e2e", "relapaw-e2e.db"),
    String(followUp.id), String(followUp.source_episode_id),
    date.toISOString().replace("T", " ").replace("Z", ""),
  ], { encoding: "utf8", windowsHide: true });
  expect(result.status, result.stderr).toBe(0);
}

async function refreshUs(page: Page) {
  await page.reload();
  await page.getByRole("button", { name: "Us" }).click();
}

test("due follow-ups appear, complete or cancel, and survive refresh", async ({ page }, testInfo) => {
  test.setTimeout(90000);
  page.setDefaultTimeout(12000);
  await page.clock.install();
  const suffix = testInfo.project.name.includes("mobile") ? "mobile" : "desktop";
  await login(page, "followup-" + suffix + "@example.test");
  const pet = await createPet(page, "复评猫");
  const source = await createRecord(page, "合成原记录：在窗边停留两分钟。");
  const due = await schedule(page);
  await page.getByRole("button", { name: "Today" }).click();
  await expect(page.getByText("今天没有需要回看的记录。")).toBeVisible();
  await setTestDueTime(page, due, new Date(Date.now() - 60000));
  await page.clock.fastForward(30100);
  const card = page.locator(".today-followups article");
  await expect(card).toHaveCount(1);
  await expect(card).toContainText("今日到期");
  await page.reload();
  await expect(card).toHaveCount(1);
  await card.getByRole("button", { name: "开始复评" }).click();
  await page.getByRole("radio", { name: "改善", exact: true }).check();
  await page.getByLabel("复评原始输入").fill("合成复评：今天在窗边停留一分钟。");
  await page.getByLabel("复评 Observation", { exact: true }).fill("在窗边停留一分钟。");
  await page.getByLabel("复评 Owner Interpretation").fill("我觉得停留时间缩短了。");
  const completed = page.waitForResponse((response) =>
    response.url().endsWith("/follow-ups/" + due.id + "/complete") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "保存复评" }).click();
  const result = await (await completed).json();
  expect(result.result_of_follow_up).toMatchObject({ id: due.id, status: "COMPLETED", outcome: "IMPROVED", source_episode_id: source.id });
  await testInfo.attach("completed-followup", { body: await page.screenshot(), contentType: "image/png" });
  await page.getByRole("button", { name: "查看原记录" }).click();
  await expect(page.getByRole("heading", { name: "当时记下的话" }).locator("..")).toContainText("合成原记录");
  await page.getByRole("button", { name: "查看复评记录" }).click();
  await expect(page.getByRole("heading", { name: "当时记下的话" }).locator("..")).toContainText("合成复评");
  await page.reload();
  await expect(card).toHaveCount(0);
  const history = await (await page.request.get("/api/v1/pets/" + pet.id + "/follow-ups")).json();
  expect(history).toContainEqual(expect.objectContaining({ id: due.id, status: "COMPLETED", result_episode_id: result.id }));
  await page.getByRole("button", { name: "Timeline" }).click();
  await page.locator(".timeline li").filter({ hasText: "合成原记录" }).getByRole("button").click();
  const overdue = await schedule(page);
  await setTestDueTime(page, overdue, new Date(Date.now() - 2 * 86400000));
  await page.getByRole("button", { name: "Today" }).click();
  await expect(card).toContainText("已逾期");
  await card.getByRole("button", { name: "取消复评" }).click();
  await page.getByRole("button", { name: "确认取消复评" }).click();
  await expect(card).toHaveCount(0);
  await page.reload();
  await expect(card).toHaveCount(0);
  const cancelled = await (await page.request.get("/api/v1/pets/" + pet.id + "/follow-ups")).json();
  expect(cancelled).toContainEqual(expect.objectContaining({ id: overdue.id, status: "CANCELLED", result_episode_id: null }));
  expect((await page.request.get("/api/v1/episodes/" + source.id)).status()).toBe(200);
});

function dateInput(daysAgo: number) {
  const date = new Date(Date.now() - daysAgo * 86400000);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

async function relationship(page: Page, text: string, daysAgo: number, kind = "OWNER_PET", otherId?: number) {
  const section = page.getByRole("region", { name: "关系事件时间线", exact: true });
  await section.getByRole("combobox", { name: /^关系类型/ }).selectOption(kind);
  if (otherId) await section.getByLabel("另一位参与者").selectOption(String(otherId));
  await section.getByLabel("发生时间", { exact: true }).fill(dateInput(daysAgo));
  await section.getByLabel("看到的互动", { exact: true }).fill(text);
  await section.getByLabel("我的理解（关系）").fill("这是主人当前的理解。");
  const saved = page.waitForResponse((response) =>
    response.url().endsWith("/api/v1/relationship-events") && response.request().method() === "POST",
  );
  await section.getByRole("button", { name: "记录关系事件", exact: true }).click();
  expect((await saved).status()).toBe(201);
  await expect(section.locator(".memory-card").filter({ has: page.getByRole("button", { name: "编辑关系事件" }) }).filter({ hasText: text })).toBeVisible();
}

async function uploadImage(panel: Locator, name: string) {
  await panel.getByLabel("添加照片或视频").setInputFiles({
    name, mimeType: "image/png",
    buffer: readFileSync("public/brand/relapaw-welcome-corgi-v4.png"),
  });
  await expect(panel.getByText(name, { exact: true })).toBeVisible();
  const image = panel.locator("img").first();
  await image.scrollIntoViewIfNeeded();
  await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBeGreaterThan(0);
  return (await panel.getByRole("link", { name: "打开或下载原文件" }).getAttribute("href"))!;
}

test("relationship history, pattern decisions, shared pets and event media persist", async ({ page }, testInfo) => {
  test.setTimeout(150000);
  page.setDefaultTimeout(12000);
  const suffix = testInfo.project.name.includes("mobile") ? "mobile" : "desktop";
  await login(page, "relationships-" + suffix + "@example.test");
  const first = await createPet(page, "关系猫甲");
  const source = await createRecord(page, "合成关系来源记录。");
  await page.getByRole("button", { name: "Us" }).click();
  const section = page.getByRole("region", { name: "关系事件时间线", exact: true });
  await section.getByLabel("看到的互动", { exact: true }).fill("来源无效时保留的输入。");
  await section.getByLabel("来源记录编号（可选）").fill("999999");
  await section.getByRole("button", { name: "记录关系事件", exact: true }).click();
  await expect(section.getByRole("alert")).toContainText("关系事件保存失败");
  await expect(section.getByLabel("看到的互动", { exact: true })).toHaveValue("来源无效时保留的输入。");
  await section.getByLabel("来源记录编号（可选）").fill(String(source.id));
  await relationship(page, "十天前主动靠近。", 10);
  await relationship(page, "五天前主动靠近。", 5);
  await relationship(page, "昨天在相同位置保持距离。", 1);
  let event = section.locator(".memory-card").filter({ has: page.getByRole("button", { name: "编辑关系事件" }) }).filter({ hasText: "十天前主动靠近。" });
  await event.getByRole("button", { name: "编辑关系事件" }).click();
  await section.getByLabel("看到的互动", { exact: true }).fill("十天前主动靠近并停留。");
  await section.getByRole("button", { name: "保存修订", exact: true }).click();
  event = section.locator(".memory-card").filter({ has: page.getByRole("button", { name: "编辑关系事件" }) }).filter({ hasText: "十天前主动靠近并停留。" });
  await event.getByText("修订历史（2）", { exact: true }).click();
  await expect(event).toContainText("十天前主动靠近。");
  await event.getByText("照片和视频证据", { exact: true }).click();
  const relationUrl = await uploadImage(event.getByRole("region", { name: "这次互动的媒体证据" }), "关系证据.png");
  await refreshUs(page);
  await expect(section).toContainText("十天前主动靠近并停留。");
  const patterns = page.getByRole("region", { name: "互动模式候选", exact: true });
  await patterns.getByText("根据已有记录建立候选", { exact: true }).click();
  const roles = patterns.locator("select[aria-label^='记录 ']");
  await expect(roles).toHaveCount(3);
  await roles.nth(1).selectOption("SUPPORTS");
  await roles.nth(2).selectOption("SUPPORTS");
  await patterns.getByLabel("候选标题", { exact: true }).fill("主动靠近的候选");
  await patterns.getByLabel("具体可观察的重复现象").fill("两次记录里主动靠近。");
  await patterns.getByLabel("反例或仍不一致的地方").fill("一次保持距离。");
  await patterns.getByRole("button", { name: "建立候选", exact: true }).click();
  await expect(patterns.getByText("至少选择 3 条记录，其中至少 2 条支持候选；反例也会被保留。", { exact: true })).toBeVisible();
  await roles.nth(0).selectOption("CONTRADICTS");
  await patterns.getByRole("button", { name: "建立候选", exact: true }).click();
  let candidate = patterns.locator(".pattern-card").filter({ hasText: "主动靠近的候选" });
  await expect(candidate).toContainText("等待你判断");
  await candidate.getByRole("button", { name: "确认候选", exact: true }).click();
  await candidate.getByRole("button", { name: "纳入长期变化", exact: true }).click();
  await refreshUs(page);
  candidate = patterns.locator(".pattern-card").filter({ hasText: "主动靠近的候选" });
  await expect(candidate).toContainText("你已确认 · 已纳入长期变化");
  await candidate.scrollIntoViewIfNeeded();
  await testInfo.attach("confirmed-interaction-pattern", { body: await page.screenshot(), contentType: "image/png" });
  await candidate.getByRole("button", { name: "修订", exact: true }).click();
  await candidate.getByLabel("标题", { exact: true }).fill("主动靠近的修订候选");
  await candidate.getByLabel("这次修改了什么").fill("补充观察范围");
  await candidate.getByRole("button", { name: "保存修订", exact: true }).click();
  candidate = patterns.locator(".pattern-card").filter({ hasText: "主动靠近的修订候选" });
  await candidate.getByText("查看证据、版本与决定", { exact: true }).click();
  await expect(candidate).toContainText("补充观察范围");
  await expect(candidate).toContainText("十天前主动靠近并停留。");
  await candidate.getByRole("button", { name: "从长期变化撤回", exact: true }).click();
  await candidate.getByRole("button", { name: "撤回候选", exact: true }).click();
  await refreshUs(page);
  await expect(candidate).toContainText("已撤回 · 已从长期变化撤回");
  await patterns.getByText("根据已有记录建立候选", { exact: true }).click();
  await roles.nth(1).selectOption("SUPPORTS");
  await roles.nth(2).selectOption("SUPPORTS");
  await roles.nth(0).selectOption("CONTRADICTS");
  await patterns.getByLabel("候选标题", { exact: true }).fill("尚不接受的另一项候选");
  await patterns.getByLabel("具体可观察的重复现象").fill("另一个需要核对的观察表述。");
  await patterns.getByLabel("反例或仍不一致的地方").fill("保留保持距离的记录。");
  await patterns.getByRole("button", { name: "建立候选", exact: true }).click();
  const rejected = patterns.locator(".pattern-card").filter({ hasText: "尚不接受的另一项候选" });
  await rejected.getByRole("button", { name: "拒绝候选", exact: true }).click();
  await refreshUs(page);
  await expect(rejected).toContainText("你已拒绝 · 未纳入长期变化");
  await rejected.getByRole("button", { name: "删除候选", exact: true }).click();
  await rejected.getByRole("button", { name: "确认删除", exact: true }).click();
  await expect(rejected).toHaveCount(0);

  const life = page.getByRole("region", { name: "生活事件与时间邻近记录", exact: true });
  await life.getByLabel("事实描述").fill("合成生活事件：更换猫窝位置。");
  await life.getByRole("button", { name: "添加生活事件", exact: true }).click();
  const lifeCard = life.locator(".memory-card").filter({ hasText: "合成生活事件：更换猫窝位置。" });
  await lifeCard.getByText("照片和视频证据", { exact: true }).click();
  const lifeUrl = await uploadImage(lifeCard.getByRole("region", { name: "这次生活事件的媒体证据" }), "生活证据.png");
  await refreshUs(page);
  const gallery = page.getByRole("region", { name: "跨时间媒体", exact: true });
  await gallery.locator("li").filter({ hasText: "生活证据.png" }).getByRole("checkbox").check();
  await gallery.locator("li").filter({ hasText: "关系证据.png" }).getByRole("checkbox").check();
  const comparison = gallery.locator(".media-compare");
  await expect(comparison.locator("img")).toHaveCount(2);
  for (const image of await comparison.locator("img").all()) {
    await image.scrollIntoViewIfNeeded();
    await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBeGreaterThan(0);
  }
  await testInfo.attach("cross-time-event-media", { body: await page.screenshot(), contentType: "image/png" });

  await expect(page.getByRole("button", { name: "添加另一只宠物", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "添加另一只宠物", exact: true }).click();
  const second = await createPet(page, "关系猫乙");
  await page.getByRole("button", { name: "Us" }).click();
  await relationship(page, "两只猫在沙发两端休息。", 0, "PET_PET", first.id);
  await page.getByLabel("当前宠物").selectOption(String(first.id));
  await expect(section).toContainText("两只猫在沙发两端休息。");
  await refreshUs(page);
  await expect(page.getByLabel("当前宠物")).toHaveValue(String(first.id));
  await expect(section).toContainText("两只猫在沙发两端休息。");
  const shared = section.locator(".memory-card").filter({ has: page.getByRole("button", { name: "编辑关系事件" }) }).filter({ hasText: "两只猫在沙发两端休息。" });
  await page.getByLabel("当前宠物").selectOption(String(second.id));
  await page.getByRole("button", { name: "查看或编辑完整档案" }).click();
  const profile = page.getByRole("dialog", { name: "宠物完整档案" });
  await profile.getByRole("button", { name: "归档档案", exact: true }).click();
  await profile.getByRole("button", { name: "确认归档 关系猫乙", exact: true }).click();
  await expect(page.getByLabel("当前宠物")).toHaveValue(String(first.id));
  await expect(shared).toHaveCount(0);
  await page.getByRole("button", { name: "查看或编辑完整档案" }).click();
  await profile.getByRole("button", { name: "管理已归档档案" }).click();
  await profile.getByRole("button", { name: "恢复 关系猫乙", exact: true }).click();
  await expect(page.getByLabel("当前宠物")).toHaveValue(String(second.id));
  await expect(shared).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await shared.getByRole("button", { name: "删除关系事件" }).click();
  await expect(shared).toHaveCount(0);
  await page.getByLabel("当前宠物").selectOption(String(second.id));
  await expect(section.getByText("两只猫在沙发两端休息。", { exact: false })).toHaveCount(0);
  await page.getByLabel("当前宠物").selectOption(String(first.id));
  event = section.locator(".memory-card").filter({ has: page.getByRole("button", { name: "编辑关系事件" }) }).filter({ hasText: "十天前主动靠近并停留。" });
  page.once("dialog", (dialog) => dialog.accept());
  await event.getByRole("button", { name: "删除关系事件" }).click();
  await expect(event).toHaveCount(0);
  expect((await page.request.get(relationUrl)).status()).toBe(404);
  await candidate.getByText("查看证据、版本与决定", { exact: true }).click();
  await expect(candidate).toContainText("十天前主动靠近并停留。");
  await candidate.getByRole("button", { name: "删除候选", exact: true }).click();
  await candidate.getByRole("button", { name: "确认删除", exact: true }).click();
  await expect(candidate).toHaveCount(0);
  await expect(section).toContainText("五天前主动靠近。");
  page.once("dialog", (dialog) => dialog.accept());
  await lifeCard.getByRole("button", { name: "删除生活事件" }).click();
  await expect(lifeCard).toHaveCount(0);
  expect((await page.request.get(lifeUrl)).status()).toBe(404);
  await refreshUs(page);
  await expect(candidate).toHaveCount(0);
  await expect(section).toContainText("五天前主动靠近。");
  await expect(gallery.locator("li")).toHaveCount(0);
});
