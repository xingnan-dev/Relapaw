import { expect, test, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";

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

test("isolated empty-account record journey, responsive layout, keyboard and accessible state", async ({ page, baseURL }, testInfo) => {
  test.setTimeout(120000);
  const mobile = testInfo.project.name.includes("mobile");
  const email = mobile ? "alpha-e2e-mobile@example.test" : "alpha-e2e-desktop@example.test";
  const petName = mobile ? "Pixel" : "Mochi";
  await login(page, email);

  await expect(page.getByRole("heading", { name: "先看见，再慢慢理解" })).toBeVisible();
  if (mobile) {
    for (const viewport of [{ width: 360, height: 640 }, { width: 390, height: 844 }, { width: 430, height: 932 }]) {
      await page.setViewportSize(viewport);
      const [canvasBox, stageBox, actionsBox] = await Promise.all([
        page.getByRole("main", { name: "首次使用引导" }).boundingBox(),
        page.locator(".onboarding-stage").boundingBox(),
        page.locator(".onboarding-actions").boundingBox(),
      ]);
      expect(canvasBox && stageBox && actionsBox).toBeTruthy();
      expect(canvasBox!.x).toBeGreaterThanOrEqual(0);
      expect(canvasBox!.x + canvasBox!.width).toBeLessThanOrEqual(viewport.width);
      expect(actionsBox!.y + actionsBox!.height).toBeLessThanOrEqual(viewport.height);
      expect(stageBox!.y + stageBox!.height).toBeLessThanOrEqual(actionsBox!.y + 1);
      const overflow = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight }));
      expect(overflow.width).toBeLessThanOrEqual(viewport.width);
      expect(overflow.height).toBeLessThanOrEqual(viewport.height);
    }
    await page.setViewportSize({ width: 400, height: 640 });
  }
  const onboardingStage = page.locator(".onboarding-stage");
  const firstStageBox = await onboardingStage.boundingBox();
  const firstArtBox = await page.locator('.onboarding-story:not([aria-hidden="true"]) .onboarding-story__art').boundingBox();
  await page.getByRole("button", { name: "翻到下一页" }).click();
  await expect(page.getByRole("heading", { name: "看见变化，不替它说话" })).toBeVisible();
  const secondStageBox = await onboardingStage.boundingBox();
  const secondArtBox = await page.locator('.onboarding-story:not([aria-hidden="true"]) .onboarding-story__art').boundingBox();
  expect(firstStageBox).not.toBeNull();
  expect(secondStageBox).not.toBeNull();
  expect(Math.abs(firstStageBox!.width - secondStageBox!.width)).toBeLessThanOrEqual(1);
  expect(Math.abs(firstStageBox!.height - secondStageBox!.height)).toBeLessThanOrEqual(1);
  expect(firstArtBox && secondArtBox).toBeTruthy();
  expect(Math.abs(firstArtBox!.width - secondArtBox!.width)).toBeLessThanOrEqual(1);
  expect(Math.abs(firstArtBox!.height - secondArtBox!.height)).toBeLessThanOrEqual(1);
  await page.getByRole("button", { name: "翻到下一页" }).click();
  await expect(page.getByRole("heading", { name: "不舒服时，安全最重要" })).toBeVisible();
  await page.getByRole("button", { name: "开始建立档案" }).click();

  const opening = page.getByRole("button", { name: /和它一起开始/ });
  const emptySetup = page.getByRole("heading", { name: "先认识它" });
  if (!(await emptySetup.isVisible())) {
    try { await opening.waitFor({ state: "visible", timeout: 3000 }); await opening.click(); } catch { /* already dismissed */ }
    const addPet = page.getByRole("button", { name: "添加我的宠物" });
    if (await addPet.isVisible()) await addPet.click();
  }
  await expect(emptySetup).toBeVisible();
  await page.getByLabel("名字", { exact: true }).fill(petName);
  await page.getByLabel("物种", { exact: true }).fill("猫");
  await page.getByRole("button", { name: "继续补充一点" }).click();
  await page.getByLabel(/宠物照片/).setInputFiles("public/brand/relapaw-welcome-corgi-v4.png");
  await expect(page.getByAltText("待上传的宠物头像预览")).toBeVisible();
  let failedAvatarUpload = false;
  if (!mobile) {
    await page.route("**/api/v1/pets/*/avatar", async (route) => {
      if (!failedAvatarUpload && route.request().method() === "PUT") {
        failedAvatarUpload = true;
        await route.abort("failed");
      } else {
        await route.continue();
      }
    });
  }
  await page.getByRole("button", { name: "完成建档" }).click();
  if (!mobile) {
    await expect(page.getByRole("alert")).toContainText("宠物档案已保存，但照片上传失败");
    const petsAfterFailure = await page.request.get("/api/v1/pets");
    expect(petsAfterFailure.ok()).toBe(true);
    expect((await petsAfterFailure.json()) as Array<{ name: string }>).toContainEqual(expect.objectContaining({ name: "Mochi" }));
    await page.getByRole("button", { name: "重试上传照片" }).click();
  }

  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  try { await opening.waitFor({ state: "visible", timeout: 3000 }); await opening.click(); } catch { /* already dismissed */ }
  await expect(page.getByRole("heading", { name: mobile ? "Pixel" : "Mochi" })).toBeVisible();
  await expect(page.getByLabel("当前宠物")).toBeVisible();
  await expect(page.getByRole("button", { name: "安全退出" })).toBeVisible();
  await expect(page.getByRole("button", { name: "重看三页介绍" })).toBeVisible();
  if (!mobile) {
    const [headerBox, petBox, logoutBox] = await Promise.all([
      page.getByRole("banner").boundingBox(),
      page.getByLabel("当前宠物").boundingBox(),
      page.getByRole("button", { name: "安全退出" }).boundingBox(),
    ]);
    expect(headerBox && petBox && logoutBox).toBeTruthy();
    expect(headerBox!.height).toBeLessThanOrEqual(110);
    expect(Math.abs((petBox!.y + petBox!.height / 2) - (logoutBox!.y + logoutBox!.height / 2))).toBeLessThanOrEqual(18);
  }
  if (mobile) {
    const [dateBox, focusBox, recentBox] = await Promise.all([
      page.locator(".date-rail").boundingBox(),
      page.locator(".focus-card").boundingBox(),
      page.locator(".today-followups").boundingBox(),
    ]);
    expect(dateBox && focusBox && recentBox).toBeTruthy();
    expect(dateBox!.y + dateBox!.height).toBeLessThanOrEqual(focusBox!.y + 1);
    expect(focusBox!.y + focusBox!.height).toBeLessThanOrEqual(recentBox!.y + 1);
  }
  await page.getByRole("button", { name: "Us" }).click();
  await expect(page.getByAltText(`${mobile ? "Pixel" : "Mochi"} 的头像`)).toBeVisible();
  await expect(page.getByRole("navigation", { name: "我们页面分区" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "它是谁，平时是什么样" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "把多次记录放回时间里" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "一起生活的人、动物与情境" })).toBeVisible();
  await page.evaluate(() => {
    window.history.replaceState(null, "", "#pet-profile-layer");
    document.querySelector("#pet-profile-layer")?.scrollIntoView();
  });
  await page.getByRole("button", { name: "Today" }).click();
  await expect(page.getByRole("heading", { name: mobile ? "Pixel" : "Mochi" })).toBeVisible();
  expect(await page.evaluate(() => window.location.hash)).toBe("");
  expect(await page.locator("main.page-transition").evaluate((node) => node.scrollTop)).toBe(0);
  if (!mobile) {
    const [focusBox, followBox, planBox, recentBox] = await Promise.all([
      page.locator(".focus-card").boundingBox(), page.locator(".today-followups").boundingBox(),
      page.locator(".today-plan").boundingBox(), page.locator(".today-recent").boundingBox(),
    ]);
    expect(focusBox && followBox && planBox && recentBox).toBeTruthy();
    expect(recentBox!.y).toBeGreaterThanOrEqual(Math.max(focusBox!.y + focusBox!.height, planBox!.y + planBox!.height) - 1);
    expect(recentBox!.x).toBeLessThanOrEqual(focusBox!.x + 1);
    expect(recentBox!.x + recentBox!.width).toBeGreaterThanOrEqual(followBox!.x + followBox!.width - 1);
  }
  await page.getByRole("button", { name: "Us" }).click();
  await page.getByRole("button", { name: /查看它的档案/ }).click();
  const profileDialog = page.getByRole("dialog", { name: "宠物完整档案" });
  await expect(profileDialog).toBeVisible();
  expect(await page.locator("main.page-transition").evaluate((node) => getComputedStyle(node).overflowY)).toBe("hidden");
  const [profileBox, closeBox, stickerBox] = await Promise.all([
    profileDialog.boundingBox(), profileDialog.getByRole("button", { name: "关闭" }).boundingBox(), profileDialog.locator(".journal-sticker").boundingBox(),
  ]);
  const profileViewport = page.viewportSize()!;
  expect(profileBox && closeBox && stickerBox).toBeTruthy();
  expect(profileBox!.x).toBeGreaterThanOrEqual(0);
  expect(profileBox!.y).toBeGreaterThanOrEqual(0);
  expect(profileBox!.x + profileBox!.width).toBeLessThanOrEqual(profileViewport.width);
  expect(profileBox!.y + profileBox!.height).toBeLessThanOrEqual(profileViewport.height);
  expect(closeBox!.x).toBeGreaterThanOrEqual(stickerBox!.x + stickerBox!.width - 1);
  await profileDialog.getByRole("button", { name: "关闭" }).click();
  expect(await page.locator("main.page-transition").evaluate((node) => node.style.overflow)).toBe("");
  const usOverflow = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
  expect(usOverflow.content).toBeLessThanOrEqual(usOverflow.viewport + 1);
  const openCaregiver = page.getByRole("button", { name: "查看照护背景与偏好", exact: true });
  if (mobile) await page.setViewportSize({ width: 375, height: 500 });
  await openCaregiver.click();
  const caregiverDialog = page.getByRole("dialog", { name: "照护背景与偏好" });
  await expect(caregiverDialog).toBeVisible();
  await expect(caregiverDialog.getByRole("button", { name: "关闭" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  expect(await caregiverDialog.evaluate((dialog) => dialog.contains(document.activeElement))).toBe(true);
  const dialogBox = await caregiverDialog.boundingBox();
  const viewport = page.viewportSize()!;
  expect(dialogBox).not.toBeNull();
  expect(dialogBox!.x).toBeGreaterThanOrEqual(0);
  expect(dialogBox!.y).toBeGreaterThanOrEqual(0);
  expect(dialogBox!.x + dialogBox!.width).toBeLessThanOrEqual(viewport.width);
  expect(dialogBox!.y + dialogBox!.height).toBeLessThanOrEqual(viewport.height);
  await page.getByLabel(/当前最关心的问题/).fill("希望安排可持续的夜间观察");
  await page.getByLabel(/我明确同意 AI/).check();
  await page.getByLabel("当前关心的问题", { exact: true }).check();
  await page.getByRole("button", { name: "保存照护背景" }).click();
  await expect(page.getByRole("status")).toContainText("照护背景已保存");
  await page.keyboard.press("Escape");
  await expect(caregiverDialog).toBeHidden();
  await expect(openCaregiver).toBeFocused();
  if (mobile) await page.setViewportSize({ width: 400, height: 640 });
  await page.reload();
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  try { await opening.waitFor({ state: "visible", timeout: 3000 }); await opening.click(); } catch { /* already dismissed */ }
  await page.getByRole("button", { name: "重看三页介绍" }).click();
  await expect(page.getByRole("main", { name: "关于 Relapaw" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "先看见，再慢慢理解" })).toBeVisible();
  await page.getByRole("button", { name: "翻到下一页" }).click();
  await expect(page.getByRole("heading", { name: "看见变化，不替它说话" })).toBeVisible();
  await page.getByRole("button", { name: "翻到下一页" }).click();
  await expect(page.getByRole("heading", { name: "不舒服时，安全最重要" })).toBeVisible();
  await page.getByRole("button", { name: "看完了" }).click();
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
  const recordSteps = page.locator(".step-rail button");
  await expect(recordSteps).toHaveCount(5);
  const stepBoxes = await recordSteps.evaluateAll((nodes) => nodes.map((node) => node.getBoundingClientRect()).map((box) => ({ top: box.top, bottom: box.bottom, width: box.width })));
  expect(stepBoxes.every((box) => Math.abs(box.top - stepBoxes[0].top) <= 1 && Math.abs(box.bottom - stepBoxes[0].bottom) <= 1 && box.width >= 44)).toBe(true);

  await expect(page.getByText("这是一条独立记录", { exact: true })).toBeVisible();
  await expect(page.getByLabel("关联观察计划")).toHaveCount(0);
  await page.getByRole("button", { name: "新建观察计划" }).click();
  await expect(page.getByLabel("观察目标")).toBeVisible();
  await page.getByLabel("观察目标").fill("观察窗边停留");
  await page.getByLabel("观察项目 1").fill("记录停留时长");
  await page.getByRole("button", { name: "保存计划" }).click();
  await expect(page.getByText("观察计划已保存。", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Understand" }).click();
  await expect(page.getByRole("radio", { name: /观察窗边停留/ })).toBeVisible();

  const rawDescription = page.getByLabel("原始描述");
  if (mobile) {
    await page.setViewportSize({ width: 360, height: 640 });
    await rawDescription.focus();
    await rawDescription.fill("Mochi 在窗边安静坐了两分钟，我猜它在等声音。" );
    const focusedInputLayout = await rawDescription.evaluate((node) => {
      const textarea = node.getBoundingClientRect();
      const label = node.closest("label")?.getBoundingClientRect();
      return {
        textareaWidth: textarea.width,
        labelWidth: label?.width ?? 0,
        textareaRight: textarea.right,
        labelRight: label?.right ?? 0,
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: document.documentElement.clientWidth,
      };
    });
    expect(focusedInputLayout.textareaWidth).toBeGreaterThanOrEqual(focusedInputLayout.labelWidth - 1);
    expect(focusedInputLayout.textareaRight).toBeLessThanOrEqual(focusedInputLayout.labelRight + 1);
    expect(focusedInputLayout.documentWidth).toBeLessThanOrEqual(focusedInputLayout.viewportWidth + 1);
    await page.setViewportSize({ width: 400, height: 640 });
  } else {
    await rawDescription.fill("Mochi 在窗边安静坐了两分钟，我猜它在等声音。" );
  }
  await page.getByText("补充事实（可选）", { exact: true }).click();
  await expect(page.getByLabel("发生时间")).toBeVisible();
  await expect(page.getByLabel("记录类型")).toBeVisible();
  await page.getByLabel("发生了什么").fill("在窗边坐着，身体朝向窗外，持续两分钟。" );
  await page.getByText("我的理解（可选）", { exact: true }).click();
  await page.getByLabel("你的理解").fill("我猜它在等待外面的声音。" );
  await page.getByText("补充次数、时长或当时情境（可选）", { exact: true }).click();
  await page.getByText("用于长期比较的精确数据（进阶，可选）", { exact: true }).click();
  await page.getByLabel("计量值").fill("2");
  await page.getByLabel("标准单位").selectOption("minutes");
  await page.getByRole("radio", { name: /观察窗边停留/ }).check();
  await expect(page.getByRole("radio", { name: "未发现上述紧急情况" })).toBeChecked();
  await page.getByRole("button", { name: "保存这条记录" }).click();
  await expect(page.getByRole("heading", { name: "记录详情" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "看到的事实" }).locator("..").getByText("在窗边坐着，身体朝向窗外，持续两分钟。" )).toBeVisible();
  await expect(page.getByRole("heading", { name: "当时的理解" }).locator("..").getByText("我猜它在等待外面的声音。" )).toBeVisible();
  await expect(page.getByText("未发现所列紧急情况")).toBeVisible();
  await expect(page.getByText("AI 当前关闭", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "生成辅助整理" })).toHaveCount(0);

  const mediaPanel = page.getByRole("heading", { name: "照片和视频证据" }).locator("..");
  const image = await readFile("public/brand/relapaw-welcome-corgi-v4.png");
  await mediaPanel.getByLabel("添加照片或视频").setInputFiles({
    name: "窗边记录.png", mimeType: "image/png", buffer: image,
  });
  await expect(mediaPanel.getByText("窗边记录.png")).toBeVisible();
  const preview = mediaPanel.getByRole("img", { name: "窗边记录.png 预览" });
  await preview.scrollIntoViewIfNeeded();
  await expect.poll(() => preview.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBeGreaterThan(0);
  const mediaUrl = (await mediaPanel.getByRole("link", { name: "打开或下载原文件" }).getAttribute("href"))!;
  expect((await (await page.request.get(mediaUrl)).body()).equals(image)).toBe(true);
  await mediaPanel.getByLabel("我的原始说明").fill("窗边坐姿的原始照片说明。" );
  await mediaPanel.getByRole("button", { name: "保存媒体说明" }).click();
  await expect(mediaPanel.getByRole("status")).toContainText("旧版本仍可查看");
  await expect(mediaPanel.getByText("修改历史（2）", { exact: true })).toBeVisible();

  await test.step("a synthetic WebM can be previewed and deleted", async () => {
    const recording = await page.context().browser()!.newContext({
      recordVideo: { dir: testInfo.outputPath("video-fixture"), size: { width: 320, height: 240 } },
    });
    const recorder = await recording.newPage();
    const video = recorder.video()!;
    try {
      await recorder.setContent('<div style="width:100px;height:100px;background:teal">Synthetic media</div>');
      await recorder.waitForTimeout(1300);
    } finally {
      await recording.close();
    }
    await mediaPanel.getByLabel("添加照片或视频").setInputFiles({
      name: "合成视频.webm", mimeType: "video/webm", buffer: await readFile(await video.path()),
    });
    const videoCard = mediaPanel.locator("article").filter({ hasText: "合成视频.webm" });
    await expect(videoCard).toBeVisible();
    await expect.poll(() => videoCard.locator("video").evaluate((element: HTMLVideoElement) => element.readyState)).toBeGreaterThan(0);
    const videoUrl = (await videoCard.getByRole("link", { name: "打开或下载原文件" }).getAttribute("href"))!;
    page.once("dialog", (dialog) => dialog.accept());
    await videoCard.getByRole("button", { name: "删除媒体" }).click();
    await expect(videoCard).toHaveCount(0);
    expect((await page.request.get(videoUrl)).status()).toBe(404);
  });

  const history = page.getByText("修改历史（1 个版本）", { exact: true }).locator("..");
  const technical = page.getByText("技术与来源信息", { exact: true }).locator("..");
  await expect(history).not.toHaveAttribute("open", "");
  await expect(technical).not.toHaveAttribute("open", "");
  await page.getByRole("button", { name: "编辑记录" }).click();
  await page.getByLabel("修改说明").fill("补充确认后的说明");
  await page.getByRole("button", { name: "保存并保留旧版本" }).click();
  await expect(page.getByText("修改历史（2 个版本）", { exact: true })).toBeVisible();
  await page.getByText("修改历史（2 个版本）", { exact: true }).click();
  await expect(page.getByText(/补充确认后的说明/)).toBeVisible();

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
  expect(await page.getByRole("heading", { name: "记录详情" }).locator("..").ariaSnapshot()).toContain("看到的事实");

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
    expect(boxes.every((box) => box.left >= 0 && box.right <= viewportWidth && box.width >= 44 && box.height >= 44)).toBe(true);
    expect(boxes.every((box, index) => index === 0 || box.left >= boxes[index - 1].right || box.top >= boxes[index - 1].bottom)).toBe(true);

    const responsiveViewports = [
      { width: 320, height: 568 }, { width: 360, height: 640 }, { width: 375, height: 667 },
      { width: 390, height: 844 }, { width: 400, height: 640 }, { width: 414, height: 896 },
      { width: 430, height: 932 }, { width: 844, height: 390 }, { width: 768, height: 1024 },
    ];
    for (const target of responsiveViewports) {
      await page.setViewportSize(target);
      for (const tab of ["Today", "Understand", "Timeline", "Us"]) {
        await page.getByRole("button", { name: tab }).click();
        const dimensions = await page.evaluate(() => ({
          documentWidth: document.documentElement.scrollWidth,
          viewportWidth: document.documentElement.clientWidth,
          mainWidth: document.querySelector("main.page-transition")?.scrollWidth ?? 0,
          mainClientWidth: document.querySelector("main.page-transition")?.clientWidth ?? 0,
        }));
        expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth + 1);
        expect(dimensions.mainWidth).toBeLessThanOrEqual(dimensions.mainClientWidth + 1);
      }
      if (target.width < 720) {
        const headerControls = await Promise.all([
          page.getByLabel("当前宠物").boundingBox(),
          page.getByRole("button", { name: "安全退出" }).boundingBox(),
          page.getByRole("button", { name: "重看三页介绍" }).boundingBox(),
        ]);
        expect(headerControls.every(Boolean)).toBe(true);
        expect(headerControls.every((box) => box!.x >= 0 && box!.x + box!.width <= target.width)).toBe(true);
        expect(headerControls.every((box) => box!.height >= 44)).toBe(true);
      }
    }

    await page.setViewportSize({ width: 390, height: 640 });
    await page.evaluate(() => { document.documentElement.style.fontSize = "20px"; });
    await page.getByRole("button", { name: "Today" }).click();
    await expect(page.getByRole("button", { name: "快速记录" })).toBeInViewport();
    const enlargedTextLayout = await page.evaluate(() => ({
      content: document.documentElement.scrollWidth,
      viewport: document.documentElement.clientWidth,
    }));
    expect(enlargedTextLayout.content).toBeLessThanOrEqual(enlargedTextLayout.viewport + 1);
    await page.evaluate(() => { document.documentElement.style.fontSize = ""; });
  }

  // Reuse this already authenticated synthetic account so route coverage does not weaken invite controls.
  for (const path of ["/", "/visual-variants", "/onboarding-variants", "/first-meeting-preview"]) {
    const response = await page.goto(path);
    expect(response?.ok()).toBe(true);
    await expect(page.locator("#root > *").first()).toBeVisible();
  }

  await page.goto("/");
  await page.getByRole("button", { name: "Today" }).click();
  const plan = page.locator(".today-plan article").filter({ hasText: "观察窗边停留" });
  await plan.getByRole("button", { name: "完成计划" }).click();
  await expect(plan).toHaveCount(0);
  await page.getByRole("button", { name: "Timeline" }).click();
  await page.getByLabel("搜索 Timeline").fill("窗边安静");
  await page.getByRole("button", { name: "搜索", exact: true }).click();
  await page.getByRole("button", { name: /打开记录/ }).click();
  await page.getByRole("button", { name: "安排复评" }).click();
  await page.getByRole("button", { name: "次日" }).click();
  await page.getByRole("button", { name: "确认安排" }).click();
  await expect(page.getByRole("heading", { name: "记录详情" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "复评关系" }).locator("..")).toContainText("PENDING");
  await page.getByRole("button", { name: "Us" }).click();
  await test.step("manual memory can be included and withdrawn with AI off", async () => {
    const memory = page.getByRole("region", { name: "待你确认的长期记忆" });
    const statement = "窗边放着蓝色毯子时，它会趴在上面。";
    await memory.getByLabel("你的原话").fill(statement);
    await memory.getByRole("button", { name: "建立手工候选" }).click();
    await expect(memory.getByText(statement, { exact: true })).toBeVisible();
    await memory.getByRole("button", { name: "纳入长期记忆", exact: true }).click();
    await expect(memory.locator(".state-heading").getByText("已纳入", { exact: true })).toBeVisible();
    await memory.getByRole("button", { name: "撤回长期记忆" }).click();
    await expect(memory.locator(".state-heading").getByText("已撤回", { exact: true })).toBeVisible();
  });

  const privacy = page.getByRole("dialog", { name: "数据与隐私" });
  await page.getByRole("button", { name: /数据与隐私/ }).click();
  const download = page.waitForEvent("download");
  await privacy.getByRole("button", { name: "下载我的数据" }).click();
  const exported = await download;
  expect(exported.suggestedFilename()).toBe("relapaw-account-export.json");
  const data = JSON.parse(await readFile(await exported.path(), "utf8"));
  expect(data.pets.map((pet: { name: string }) => pet.name)).toEqual([petName]);
  expect(data.episode_revisions).toHaveLength(2);
  expect(data.media_attachments).toHaveLength(1);
  expect(data.memory_candidates).toHaveLength(1);
  expect(data.identities[0]).not.toHaveProperty("subject");
  await privacy.getByRole("button", { name: "关闭" }).click();

  await test.step("a separately signed-in account cannot see the first account's data", async () => {
    const other = await page.context().browser()!.newContext({ baseURL });
    try {
      const otherPage = await other.newPage();
      await login(otherPage, "isolation-e2e@example.test");
      await expect.poll(async () => (await otherPage.request.get("/api/v1/pets")).status()).toBe(200);
      expect(await (await otherPage.request.get("/api/v1/pets")).json()).toEqual([]);
      expect((await otherPage.request.get(`/api/v1/pets/${data.pets[0].id}`)).status()).toBe(404);
      expect((await otherPage.request.get(`/api/v1/episodes/${data.episodes[0].id}`)).status()).toBe(404);
      expect((await otherPage.request.get(mediaUrl)).status()).toBe(404);
      expect((await page.request.get(mediaUrl)).status()).toBe(200);
    } finally {
      await other.close();
    }
  });

  await test.step("the only pet can be archived and restored without creating another pet", async () => {
    const profile = page.getByRole("dialog", { name: "宠物完整档案" });
    const openProfile = page.getByRole("button", { name: /查看它的档案/ });
    await openProfile.click();
    await profile.getByRole("button", { name: "归档档案", exact: true }).click();
    await profile.getByRole("button", { name: `确认归档 ${petName}` }).click();
    await expect(page.getByLabel("当前宠物")).toHaveCount(0);
    if (!(await profile.isVisible())) await openProfile.click();
    await profile.getByRole("button", { name: "管理已归档档案" }).click();
    await profile.getByRole("button", { name: `恢复 ${petName}` }).click();
    await expect(page.getByLabel("当前宠物")).toHaveValue(String(data.pets[0].id));
  });

  await page.getByRole("button", { name: "安全退出" }).click();
  await expect(page.getByLabel("受邀邮箱")).toBeVisible();
  await login(page, email);
  await expect(page.getByLabel("当前宠物")).toHaveValue(String(data.pets[0].id));
  await page.getByRole("button", { name: "Timeline" }).click();
  await page.getByRole("button", { name: /打开记录/ }).click();
  await page.getByRole("button", { name: "删除记录" }).click();
  await page.getByRole("button", { name: "确认删除", exact: true }).click();
  await expect.poll(async () => (await page.request.get(`/api/v1/episodes/${data.episodes[0].id}`)).status()).toBe(404);
  expect((await page.request.get(mediaUrl)).status()).toBe(404);
  await page.getByRole("button", { name: "Us" }).click();
  await page.getByRole("button", { name: /数据与隐私/ }).click();
  const deleteAccount = privacy.getByRole("button", { name: "请求删除账户" });
  await expect(deleteAccount).toBeDisabled();
  await privacy.getByLabel("输入 DELETE MY ACCOUNT 以确认").fill("DELETE MY ACCOUNT");
  const deletion = page.waitForResponse((response) => response.url().endsWith("/api/v1/privacy/account") && response.request().method() === "DELETE");
  await deleteAccount.click();
  const response = await deletion;
  expect(response.status()).toBe(202);
  await expect(page.getByLabel("受邀邮箱")).toBeVisible();
  expect((await page.request.get("/api/v1/privacy/export")).status()).toBe(401);
});
