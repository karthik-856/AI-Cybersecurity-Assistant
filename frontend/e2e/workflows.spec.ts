import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page, username = "admin") {
  await page.goto("/login");
  await page.getByLabel(/username or email/i).fill(username);
  await page.getByLabel("Password", { exact: true }).fill("Test-Password1!");
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

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
