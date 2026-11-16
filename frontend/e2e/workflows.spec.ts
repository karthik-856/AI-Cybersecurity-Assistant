import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page, username = "admin") {
  await page.goto("/login");
  await page.getByLabel(/username or email/i).fill(username);
  await page.getByLabel("Password", { exact: true }).fill("Test-Password1!");
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test("attack chart shows shares of all alerts", async ({ page }) => {
  await page.route("**/api/dashboard/summary", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    data.alerts.total = 100;
    data.attack_distribution = [
      { name: "DOS", count: 20 },
      { name: "DDOS", count: 10 },
    ];
    await route.fulfill({ response, json: data });
  });
  await signIn(page);
  await expect(page.locator(".attack-share").first()).toHaveText("(20%)");
  await expect(page.locator(".attack-share").nth(1)).toHaveText("(10%)");
});

test("investigation drafts survive refreshes and notes persist after saving", async ({
  page,
  request,
}) => {
  await signIn(page);
  const token = await page.evaluate(() =>
    localStorage.getItem("zuka_access_token"),
  );
  const headers = { Authorization: `Bearer ${token}` };
  const incidentsResponse = await request.get("/api/incidents?limit=1", {
    headers,
  });
  expect(incidentsResponse.status()).toBe(200);
  const incidents = await incidentsResponse.json();
  const created = await request.post("/api/investigations", {
    headers,
    data: { incident_id: incidents.items[0].incident_id },
  });
  expect(created.status()).toBe(201);
  const investigation = await created.json();
  await page.goto(
    `/investigation?investigation_id=${encodeURIComponent(investigation.investigation_id)}`,
  );
  const notes = page.getByPlaceholder(
    "Record evidence reviewed, observations, correlations, and analyst actions...",
  );
  const conclusion = page.getByPlaceholder(
    "Document the evidence-based conclusion of the investigation...",
  );
  await notes.fill("Browser review: replay evidence checked.");
  await conclusion.fill("Unsaved analyst conclusion remains available.");
  await page.waitForResponse(
    (response) =>
      response.url().includes("/api/investigations?") &&
      response.request().method() === "GET",
  );
  await expect(notes).toHaveValue("Browser review: replay evidence checked.");
  await expect(conclusion).toHaveValue(
    "Unsaved analyst conclusion remains available.",
  );
  const saved = page.waitForResponse(
    (response) =>
      response.url().endsWith("/notes") &&
      response.request().method() === "PATCH",
  );
  await page.getByRole("button", { name: "Save Notes", exact: true }).click();
  expect((await saved).status()).toBe(200);
  await expect(conclusion).toHaveValue(
    "Unsaved analyst conclusion remains available.",
  );
  await page.reload();
  await expect(notes).toHaveValue("Browser review: replay evidence checked.");
});

test("all main screens load without browser errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await signIn(page);
  for (const path of [
    "/dashboard",
    "/network-monitor",
    "/alerts",
    "/incidents",
    "/investigation",
    "/defense",
    "/reports",
    "/databases",
    "/users",
    "/settings",
  ]) {
    await page.goto(path);
    await expect(page.locator("h1").first()).toBeVisible();
    await expect(page.locator("body")).not.toContainText("Unable to load");
    const width = await page.evaluate(() => ({
      viewport: innerWidth,
      document: document.documentElement.scrollWidth,
    }));
    expect(width.document, path).toBeLessThanOrEqual(width.viewport + 1);
  }
  expect(errors).toEqual([]);
});

test("assistant answers and clears its conversation", async ({ page }) => {
  await signIn(page);
  await page.getByRole("button", { name: "Open Zuka assistant" }).click();
  await page.getByLabel("Message Zuka").fill("How do I resolve an incident?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByRole("log")).toContainText("COMPLETED", {
    timeout: 30000,
  });
  await page.getByRole("button", { name: "Clear conversation" }).click();
  await expect(page.getByRole("log")).not.toContainText("COMPLETED");
  await expect(page.getByRole("log")).toContainText("Hi, I'm Zuka.");
});

test("settings persist and logout invalidates the session", async ({
  page,
  request,
}) => {
  await signIn(page);
  const token = await page.evaluate(() =>
    localStorage.getItem("zuka_access_token"),
  );
  await page.goto("/settings");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.getByRole("button", { name: "Save Changes", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Saved", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Logout", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(
    (
      await request.get("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      })
    ).status(),
  ).toBe(401);
  expect(
    await page.evaluate(() => sessionStorage.getItem("zuka_chat_history")),
  ).toBeNull();
});

test("viewer cannot reach administration", async ({ page }) => {
  await signIn(page, "viewer");
  await expect(
    page.getByRole("link", { name: "User Management", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Database Center", exact: true }),
  ).toHaveCount(0);
  await page.goto("/users");
  await expect(page).not.toHaveURL(/\/users$/);
  await page.goto("/settings");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page).toHaveURL(/\/settings$/);
});

test("revoked sessions return to sign-in", async ({ page, request }) => {
  await signIn(page);
  const token = await page.evaluate(() =>
    localStorage.getItem("zuka_access_token"),
  );
  const response = await request.post("/api/auth/logout", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status()).toBe(200);
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
});

test("a missing page bundle offers recovery instead of a blank screen", async ({
  page,
}) => {
  await signIn(page);
  await page.route("**/assets/Reports-*.js", (route) => route.abort());
  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "This page couldn’t load" }),
  ).toBeVisible();
  await page.unroute("**/assets/Reports-*.js");
  await page.getByRole("button", { name: "Reload page" }).click();
  await expect(
    page.getByRole("heading", { name: "Reports", exact: true }),
  ).toBeVisible();
});

test("mobile navigation and screens fit the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  for (const path of [
    "/dashboard",
    "/alerts",
    "/incidents",
    "/investigation",
    "/defense",
    "/reports",
    "/settings",
  ]) {
    await page.goto(path);
    await expect(page.locator("h1").first()).toBeVisible();
    const width = await page.evaluate(() => ({
      viewport: innerWidth,
      document: document.documentElement.scrollWidth,
    }));
    expect(width.document, path).toBeLessThanOrEqual(width.viewport + 1);
  }
  await page.getByRole("button", { name: "Toggle Mobile Navigation" }).click();
  await expect(
    page.getByRole("link", { name: "Dashboard", exact: true }),
  ).toBeVisible();
});
