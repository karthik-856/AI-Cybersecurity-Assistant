import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page, username = "admin") {
  await page.goto("/login");
  await page.getByLabel(/username or email/i).fill(username);
  await page.getByLabel("Password", { exact: true }).fill("Test-Password1!");
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test("included demo processing saves a real flow and explained alert", async ({
  page,
}, testInfo) => {
  await signIn(page);
  await page.goto("/network-monitor");
  // Row 5 is an attack sample in the checked-in demonstration CSV.
  await page.evaluate(() => localStorage.setItem("zuka_demo_row", "5"));
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/replay/demo") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Process next demo event", exact: true })
    .click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const result = (await response.json()).result;
  expect(result.network_event_id).toBeGreaterThan(0);
  expect(result.alert_id).toBeTruthy();
  await expect(
    page.getByRole("status").filter({ hasText: "Demo event #" }),
  ).toContainText("Alert and explanation saved.");
  await page
    .getByRole("button", { name: "View generated alert", exact: true })
    .click();
  await expect(
    page.getByRole("complementary", {
      name: "Alert investigation",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator(".alert-explanation-row")).toHaveCount(5);
  await page.locator(".alert-explanation-list").scrollIntoViewIfNeeded();
  await page.screenshot({
    path: testInfo.outputPath("demo-alert-explanation.png"),
    fullPage: true,
  });
});

test("an older seeded alert generates and retains its explanation", async ({
  page,
  request,
}) => {
  await signIn(page);
  const token = await page.evaluate(() =>
    localStorage.getItem("zuka_access_token"),
  );
  const response = await request.get("/api/alerts?limit=1000", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await response.json();
  expect(response.status()).toBe(200);
  const alert = data.alerts.find(
    (item: {
      alert_id: string;
      xai_explanation?: { top_contributions?: unknown[] };
    }) => !item.xai_explanation?.top_contributions?.length,
  );
  expect(alert).toBeTruthy();
  await page.goto(`/alerts?search=${encodeURIComponent(alert.alert_id)}`);
  await expect(
    page.getByRole("complementary", {
      name: "Alert investigation",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Generate explanation", exact: true })
    .click();
  await expect(page.locator(".alert-explanation-row")).toHaveCount(5, {
    timeout: 30000,
  });
  await page.reload();
  await expect(
    page.getByRole("complementary", {
      name: "Alert investigation",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator(".alert-explanation-row")).toHaveCount(5);
  await page
    .getByRole("button", { name: "Close investigation", exact: true })
    .click();
  await expect(
    page.getByRole("complementary", {
      name: "Alert investigation",
      exact: true,
    }),
  ).toHaveCount(0);
  await page.waitForResponse(
    (response) =>
      response.url().includes("/api/alerts?") &&
      response.request().method() === "GET",
  );
  await expect(
    page.getByRole("complementary", {
      name: "Alert investigation",
      exact: true,
    }),
  ).toHaveCount(0);
});

test("email verification explains missing configuration and accepts configured email codes", async ({
  page,
}) => {
  await signIn(page);
  await page.goto("/settings");
  await page.getByRole("button", { name: /Security & Sessions/ }).click();
  const panel = page.locator(".twofa-panel");
  await expect(
    panel.getByRole("button", { name: "Enable", exact: true }),
  ).toBeDisabled();
  await expect(panel.locator(".twofa-configuration-note")).toContainText(
    "finish SMTP setup",
  );
  await page.route("**/api/auth/features", (route) =>
    route.fulfill({
      json: { registration: true, password_recovery: true, two_factor: true },
    }),
  );
  let verified = false;
  await page.route("**/api/auth/2fa/status", (route) =>
    route.fulfill({ json: { enabled: verified, email: "test@example.com" } }),
  );
  await page.route("**/api/auth/2fa/request", (route) =>
    route.fulfill({ json: { message: "Verification email sent." } }),
  );
  await page.route("**/api/auth/2fa/verify", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      action: "enable",
      otp: "123456",
    });
    verified = true;
    await route.fulfill({
      json: { message: "Two-step verification enabled." },
    });
  });
  await page.reload();
  await page.getByRole("button", { name: /Security & Sessions/ }).click();
  await panel.getByRole("button", { name: "Enable", exact: true }).click();
  await panel
    .getByRole("textbox", { name: "Two-step verification code" })
    .fill("123456");
  await panel
    .getByRole("button", { name: "Verify & Enable", exact: true })
    .click();
  await expect(panel.locator(".twofa-status")).toContainText("Enabled");
});

test("an administrator can create a viewer account without SMTP", async ({
  page,
}, testInfo) => {
  await signIn(page);
  await page.goto("/users");
  await page.getByRole("button", { name: "Create User", exact: true }).click();
  const form = page.locator(".users-form");
  await page.screenshot({
    path: testInfo.outputPath("create-user.png"),
    fullPage: true,
  });
  const username = `browser_viewer_${Date.now()}`;
  await form.getByLabel("Username", { exact: true }).fill(username);
  await form
    .getByLabel("Email", { exact: true })
    .fill(`${username}@example.com`);
  await form
    .getByPlaceholder("Choose a unique password")
    .fill("Test-Password1!");
  await form
    .getByRole("combobox", { name: "Account role", exact: true })
    .selectOption("VIEWER");
  await form.getByRole("button", { name: "Create User", exact: true }).click();
  await expect(page.locator(".users-form-success")).toContainText(
    "created successfully",
  );
  await expect(page.locator(".users-modal-backdrop")).toHaveCount(0);
  await page.getByRole("button", { name: "Logout", exact: true }).click();
  await signIn(page, username);
  await expect(
    page.getByRole("link", { name: "User Management", exact: true }),
  ).toHaveCount(0);
});

async function mockDeviceNotifications(
  page: Page,
  permission: NotificationPermission = "default",
  enabled = false,
) {
  await page.addInitScript(
    ({ permission, enabled }) => {
      const probe = { requests: 0, shown: 0, body: "", url: "" };
      Object.defineProperty(window, "zukaNotificationProbe", { value: probe });
      Object.defineProperty(window, "Notification", {
        configurable: true,
        value: {
          get permission() {
            return sessionStorage.getItem("zuka-test-permission") || permission;
          },
          async requestPermission() {
            probe.requests++;
            const result = permission === "denied" ? "denied" : "granted";
            sessionStorage.setItem("zuka-test-permission", result);
            return result;
          },
        },
      });
      const registration = {
        pushManager: { getSubscription: async () => null },
        showNotification: async (
          _title: string,
          options: NotificationOptions,
        ) => {
          probe.shown++;
          probe.body = options.body || "";
          probe.url = String(options.data?.url || "");
        },
      };
      Object.defineProperty(navigator, "serviceWorker", {
        configurable: true,
        value: {
          register: async () => registration,
          ready: Promise.resolve(registration),
          getRegistration: async () => registration,
        },
      });
      if (enabled)
        localStorage.setItem(
          "zuka_settings_preferences_v2",
          JSON.stringify({
            browserNotifications: true,
            notificationPreview: false,
            criticalAlerts: true,
            highAlerts: true,
          }),
        );
    },
    { permission, enabled },
  );
  await page.route("**/api/push/status", (route) =>
    route.fulfill({ json: { configured: false } }),
  );
  await page.route("**/api/push/public-key", (route) =>
    route.fulfill({ status: 503, json: { detail: "Not configured" } }),
  );
}

function notificationProbe(page: Page) {
  return page.evaluate(
    () =>
      (
        window as typeof window & {
          zukaNotificationProbe: {
            requests: number;
            shown: number;
            body: string;
            url: string;
          };
        }
      ).zukaNotificationProbe,
  );
}

test("notifications request permission and offer an honest device test without server keys", async ({
  page,
}, testInfo) => {
  await mockDeviceNotifications(page);
  await signIn(page);
  await page.goto("/settings");
  await page.getByRole("button", { name: /Alert Notifications/ }).click();
  const toggle = page.getByRole("button", {
    name: "Browser notifications",
    exact: true,
  });
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  expect((await notificationProbe(page)).requests).toBe(1);
  await page
    .getByRole("button", { name: "Send test notification", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Device notification shown. Background push needs server setup.",
  );
  expect((await notificationProbe(page)).shown).toBe(1);
  await page.screenshot({
    path: testInfo.outputPath("notification-settings.png"),
    fullPage: true,
  });
  await page.evaluate(() =>
    localStorage.setItem(
      "zuka_settings_preferences",
      JSON.stringify({ browserNotifications: false }),
    ),
  );
  await page.reload();
  await page.getByRole("button", { name: /Alert Notifications/ }).click();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
});

test("denied notification permission stays disabled with actionable guidance", async ({
  page,
}) => {
  await mockDeviceNotifications(page, "denied");
  await signIn(page);
  await page.goto("/settings");
  await page.getByRole("button", { name: /Alert Notifications/ }).click();
  await page
    .getByRole("button", { name: "Browser notifications", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Browser notifications", exact: true }),
  ).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByRole("status")).toContainText(
    "Notifications are blocked.",
  );
  await expect(
    page.getByRole("button", { name: "Send test notification", exact: true }),
  ).toBeDisabled();
});

test("a new high-severity alert produces a privacy-aware foreground notification", async ({
  page,
}) => {
  await mockDeviceNotifications(page, "granted", true);
  let polls = 0;
  await page.route("**/api/alerts?*", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    const sample = data.alerts[0];
    polls++;
    data.alerts =
      polls === 1
        ? []
        : [
            {
              ...sample,
              alert_id: "NOTIFICATION-TEST",
              severity: "CRITICAL",
              predicted_class: "PRIVATE_CLASS",
              detected_at: new Date().toISOString(),
            },
          ];
    await route.fulfill({ response, json: data });
  });
  await signIn(page);
  await expect.poll(() => polls).toBeGreaterThan(0);
  expect((await notificationProbe(page)).shown).toBe(0);
  await expect
    .poll(async () => (await notificationProbe(page)).shown, { timeout: 12000 })
    .toBe(1);
  expect((await notificationProbe(page)).body).toBe(
    "A new security alert requires attention.",
  );
  expect((await notificationProbe(page)).url).toBe(
    "/alerts?search=NOTIFICATION-TEST",
  );
});

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
  await expect(
    page.getByRole("button", {
      name: "Open security notifications",
      exact: true,
    }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: /Alert Notifications/ }).click();
  await expect(
    page.getByRole("button", { name: "Browser notifications", exact: true }),
  ).toBeDisabled();
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
