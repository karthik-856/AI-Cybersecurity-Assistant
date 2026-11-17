import {
  deletePushSubscription,
  getPushPublicKey,
  getPushStatus,
  savePushSubscription,
  sendPushTest,
} from "./api";

function notificationPreferences() {
  try {
    const v1 = JSON.parse(
      localStorage.getItem("zuka_settings_preferences") || "{}",
    );
    const v2 = JSON.parse(
      localStorage.getItem("zuka_settings_preferences_v2") || "{}",
    );
    return {
      enabled: v2.browserNotifications ?? v1.browserNotifications ?? false,
      critical: v2.criticalAlerts ?? v1.notificationsCritical ?? true,
      high: v2.highAlerts ?? v1.notificationsHigh ?? true,
      preview: v2.notificationPreview ?? v1.notificationPreview ?? true,
    };
  } catch {
    return { enabled: false, critical: true, high: true, preview: true };
  }
}

function supported() {
  return (
    window.isSecureContext &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export async function requestBrowserNotificationPermission(): Promise<NotificationPermission> {
  if (Notification.permission !== "default") return Notification.permission;
  let poll: ReturnType<typeof setInterval> | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const requested = Notification.requestPermission();
    const observed = new Promise<NotificationPermission>((resolve) => {
      poll = setInterval(() => {
        if (Notification.permission !== "default")
          resolve(Notification.permission);
      }, 250);
      timer = setTimeout(() => resolve(Notification.permission), 20000);
    });
    return await Promise.race([requested, observed]);
  } finally {
    clearInterval(poll);
    clearTimeout(timer);
  }
}

async function notificationDeadline<T>(operation: Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      operation,
      new Promise<never>((_, reject) => {
        timer = setTimeout(
          () =>
            reject(
              new Error(
                "The browser notification request timed out. Reload this page and check browser notification settings.",
              ),
            ),
          10000,
        );
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

async function notificationRegistration() {
  await notificationDeadline(
    navigator.serviceWorker.register("/sw.js", {
      scope: "/",
      updateViaCache: "none",
    }),
  );
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      navigator.serviceWorker.ready,
      new Promise<never>((_, reject) => {
        timer = setTimeout(
          () =>
            reject(
              new Error(
                "Notification setup timed out. Try reloading the page.",
              ),
            ),
          10000,
        );
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

function publicKeyBytes(value: string): ArrayBuffer {
  const normalized = (value + "=".repeat((4 - (value.length % 4)) % 4))
    .replace(/-/g, "+")
    .replace(/_/g, "/");
  return Uint8Array.from(atob(normalized), (character) =>
    character.charCodeAt(0),
  ).buffer;
}

async function syncPush(): Promise<boolean> {
  const prefs = notificationPreferences();
  if (!supported() || !prefs.enabled || Notification.permission !== "granted")
    return false;
  try {
    const { public_key: publicKey } = await getPushPublicKey();
    const registration = await notificationRegistration();
    let subscription = await registration.pushManager.getSubscription();
    if (subscription?.options.applicationServerKey) {
      const oldKey = new Uint8Array(subscription.options.applicationServerKey);
      const key = new Uint8Array(publicKeyBytes(publicKey));
      if (
        oldKey.length !== key.length ||
        oldKey.some((value, index) => value !== key[index])
      ) {
        await subscription.unsubscribe();
        subscription = null;
      }
    }
    if (!subscription)
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: publicKeyBytes(publicKey),
      });
    const json = subscription.toJSON();
    if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) return false;
    await savePushSubscription({
      endpoint: json.endpoint,
      keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
      critical_alerts: prefs.critical,
      high_alerts: prefs.high,
      notification_preview: prefs.preview,
    });
    return true;
  } catch {
    return false;
  }
}

let synchronization: Promise<boolean> = Promise.resolve(false);
export function ensurePersistentPush(): Promise<boolean> {
  synchronization = synchronization.catch(() => false).then(syncPush);
  return notificationDeadline(synchronization).catch(() => false);
}

export async function disablePersistentPush(): Promise<void> {
  synchronization = synchronization
    .catch(() => false)
    .then(async () => {
      if (!("serviceWorker" in navigator) || !("PushManager" in window))
        return false;
      const registration = await navigator.serviceWorker.getRegistration("/");
      const subscription = await registration?.pushManager.getSubscription();
      if (!subscription) return false;
      const json = subscription.toJSON();
      try {
        if (json.endpoint && json.keys?.p256dh && json.keys?.auth)
          await deletePushSubscription({
            endpoint: json.endpoint,
            keys: json.keys,
          });
      } catch {
        /* The browser subscription is still revoked below when offline. */
      }
      await subscription.unsubscribe();
      return false;
    });
  await notificationDeadline(synchronization).catch(() => false);
}

export async function showForegroundAlert(alert: {
  alert_id: string;
  severity: string;
  predicted_class: string;
  confidence: number;
}): Promise<void> {
  const prefs = notificationPreferences();
  if (!supported() || !prefs.enabled || Notification.permission !== "granted")
    return;
  const registration = await notificationRegistration();
  await notificationDeadline(
    registration.showNotification(`${alert.severity} SECURITY ALERT`, {
      body: prefs.preview
        ? `${alert.predicted_class} detected`
        : "A new security alert requires attention.",
      icon: "/zuka-push-icon.svg",
      badge: "/zuka-push-badge.svg",
      tag: `zuka-${alert.alert_id}`,
      data: { url: `/alerts?search=${encodeURIComponent(alert.alert_id)}` },
    }),
  );
}

export async function testBrowserNotification(): Promise<string> {
  if (!supported() || Notification.permission !== "granted")
    throw new Error("Enable browser notification permission first.");
  const { configured } = await getPushStatus();
  if (configured) {
    if (!(await ensurePersistentPush()))
      throw new Error(
        "This device could not register for background push. Check notification permission and try again.",
      );
    const registration = await notificationRegistration();
    const subscription = await registration.pushManager.getSubscription();
    if (!subscription) throw new Error("Enable browser notifications first.");
    await sendPushTest(subscription.endpoint);
    return "Test push accepted. Check your device notifications.";
  }
  const registration = await notificationRegistration();
  await notificationDeadline(
    registration.showNotification("ZUKA test notification", {
      body: "Notifications work while this website is open. Background push still needs server setup.",
      tag: "zuka-notification-test",
      data: { url: "/settings" },
    }),
  );
  return "Device test submitted. If no banner appears, allow Chrome in your system notification settings and turn off Do Not Disturb. Background push needs server setup.";
}
