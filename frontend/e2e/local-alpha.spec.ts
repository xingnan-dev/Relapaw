import { expect, test, type Page } from "@playwright/test";

async function login(page: Page, email: string) {
  await page.goto("/");
  if (await page.getByRole("navigation", { name: "Primary navigation" }).isVisible()) return;
  await page.getByLabel("受邀邮箱").fill(email);
  await page.getByRole("button", { name: "获取验证码" }).click();
  await page.getByLabel("一次性验证码").fill("246810");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  const consent = page.getByRole("heading", { name: "开始前，请确认数据约定" });
  await Promise.race([
    consent.waitFor({ state: "visible" }),
    page.getByRole("navigation", { name: "Primary navigation" }).waitFor({ state: "visible" }),
    page.getByRole("heading", { name: "先看见，再慢慢理解" }).waitFor({ state: "visible" }),
  ]);
  if (await consent.isVisible()) {
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "接受并继续" }).click();
  }
}

async function tabTo(page: Page, accessibleName: string, limit = 30) {
  for (let index = 0; index < limit; index += 1) {
    await page.keyboard.press("Tab");
    const name = await page.evaluate(() => {
      const element = document.activeElement as HTMLElement | null;
      if (!element) return "";
      return element.getAttribute("aria-label") || element.textContent?.trim() || "";
    });
    if (name === accessibleName) return;
  }
  throw new Error(`Keyboard focus did not reach ${accessibleName}`);
}

test("isolated empty-account record journey, responsive layout, keyboard and accessible state", async ({ page }, testInfo) => {
  test.setTimeout(60000);
  const mobile = testInfo.project.name.includes("mobile");
  if (mobile) await page.addInitScript(() => localStorage.setItem("relapaw.onboarding.completed", "true"));
  await login(page, mobile ? "alpha-e2e-mobile@example.test" : "alpha-e2e-desktop@example.test");

  if (!mobile) {
    await expect(page.getByRole("heading", { name: "先看见，再慢慢理解" })).toBeVisible();
    await page.getByRole("button", { name: "跳过" }).click();
  }

  const opening = page.getByRole("button", { name: /和它一起开始/ });
  if (mobile) {
    try { await opening.waitFor({ state: "visible", timeout: 3000 }); await opening.click(); } catch { /* already dismissed */ }
    await page.getByRole("button", { name: "添加我的宠物" }).click();
  }
  const emptySetup = page.getByRole("heading", { name: "先认识它" });
  await expect(emptySetup).toBeVisible();
  await page.getByLabel("名字").fill(mobile ? "Pixel" : "Mochi");
  await page.getByLabel("物种").fill("猫");
  await page.getByRole("button", { name: "继续补充一点" }).click();
  await page.getByRole("button", { name: "完成建档" }).click();

  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  try { await opening.waitFor({ state: "visible", timeout: 3000 }); await opening.click(); } catch { /* already dismissed */ }

  // Keyboard-only navigation enters the record workspace and leaves a visible focus indicator.
  const recordNav = page.getByRole("button", { name: "Understand" });
  await tabTo(page, "Understand");
  await expect(recordNav).toBeFocused();
  const focusVisible = await recordNav.evaluate((node) => {
    const style = getComputedStyle(node);
    const outline = style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0 && style.outlineColor !== "transparent";
    const shadow = style.boxShadow !== "none" && !style.boxShadow.includes("rgba(0, 0, 0, 0)");
    return outline || shadow;
  });
  expect(focusVisible).toBe(true);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "记下一刻" })).toBeVisible();
  if (await opening.isVisible()) await opening.click();

  await page.getByLabel("原始描述").fill("Mochi 在窗边安静坐了两分钟，我猜它在等声音。" );
  await page.getByLabel("发生了什么").fill("在窗边坐着，身体朝向窗外，持续两分钟。" );
  await page.getByLabel("你的理解").fill("我猜它在等待外面的声音。" );
  await page.getByLabel("计量值").fill("2");
  await page.getByLabel("标准单位").selectOption("minutes");
  await expect(page.getByRole("radio", { name: "未发现上述紧急情况" })).toBeChecked();
  await page.getByRole("button", { name: "保存手工记录" }).click();
  await expect(page.getByRole("heading", { name: "记录详情" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "发生了什么" }).locator("..").getByText("在窗边坐着，身体朝向窗外，持续两分钟。" )).toBeVisible();
  await expect(page.getByRole("heading", { name: "你的理解" }).locator("..").getByText("我猜它在等待外面的声音。" )).toBeVisible();
  await expect(page.getByText("NORMAL")).toBeVisible();

  // Natural tab order starts with the persistent pet scope, then session control.
  await page.evaluate(() => {
    const sentinel = document.createElement("button");
    sentinel.id = "e2e-focus-sentinel";
    sentinel.style.position = "fixed";
    sentinel.style.left = "-10000px";
    document.body.prepend(sentinel);
    sentinel.focus();
  });
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("当前宠物")).toBeFocused();
  await page.locator("#e2e-focus-sentinel").evaluate((node) => node.remove());
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "安全退出" })).toBeFocused();

  // Accessibility-tree snapshots verify the key persistent navigation and record-detail regions.
  expect(await page.getByRole("banner").ariaSnapshot()).toContain('combobox "当前宠物"');
  expect(await page.getByRole("heading", { name: "记录详情" }).locator("..").ariaSnapshot()).toContain("发生了什么");

  // No positive tabindex and every visible native form control has an explicit programmatic name.
  expect(await page.locator("[tabindex]").evaluateAll((nodes) => nodes.filter((node) => Number(node.getAttribute("tabindex")) > 0).length)).toBe(0);
  const unnamed = await page.locator("button, a, input, select, textarea").evaluateAll((nodes) => nodes.filter((node) => {
    const element = node as HTMLElement;
    if (element.offsetParent === null) return false;
    const isFormField = element.matches("input, select, textarea");
    const labels = isFormField ? Array.from((element as HTMLInputElement).labels ?? []).some((label) => Boolean(label.textContent?.trim())) : false;
    const labelled = element.getAttribute("aria-label") || element.getAttribute("aria-labelledby") || labels || (!isFormField && element.textContent?.trim());
    return !labelled;
  }).map((node) => node.outerHTML.slice(0, 120)));
  expect(unnamed).toEqual([]);

  const overflow = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
  expect(overflow.content).toBeLessThanOrEqual(overflow.viewport + 1);
  if (mobile) {
    const nav = page.getByRole("navigation", { name: "Primary navigation" });
    await expect(nav).toBeInViewport();
    await expect(page.getByLabel("当前宠物")).toBeInViewport();
    const boxes = await nav.getByRole("button").evaluateAll((nodes) => nodes.map((node) => { const box = node.getBoundingClientRect(); return { left: box.left, right: box.right, top: box.top, bottom: box.bottom, width: box.width, height: box.height }; }));
    const viewportWidth = page.viewportSize()!.width;
    expect(boxes.every((box) => box.left >= 0 && box.right <= viewportWidth && box.width >= 40 && box.height >= 40)).toBe(true);
    expect(boxes.every((box, index) => index === 0 || box.left >= boxes[index - 1].right || box.top >= boxes[index - 1].bottom)).toBe(true);
  }
});
