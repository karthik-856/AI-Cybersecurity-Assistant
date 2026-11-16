import {
  deletePushSubscription,
  getPushPublicKey,
  savePushSubscription,
} from "../services/api";

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, "+")
    .replace(/_/g, "/");

  const rawData = window.atob(base64);
  const output = new Uint8Array(rawData.length);

  for (let index = 0; index < rawData.length; index += 1) {
    output[index] = rawData.charCodeAt(index);
  }

  const buffer = new ArrayBuffer(output.byteLength);
  new Uint8Array(buffer).set(output);
  return buffer;
}

export async function ensurePersistentPush(): Promise<boolean> {
  if (!("serviceWorker" in navigator)) {
    return false;
  }

  if (!("PushManager" in window)) {
    return false;
  }

  if (!("Notification" in window)) {
    return false;
  }

  const preferences = readNotificationPreferences();

  if (preferences.browserNotifications !== true) {
    return false;
  }

  try {
    if (Notification.permission !== "granted") {
      return false;
    }

    const registration = await navigator.serviceWorker.register("/sw.js", {
      scope: "/",
      updateViaCache: "none",
    });

    await navigator.serviceWorker.ready;

    const { public_key: publicKey } = await getPushPublicKey();

    let subscription = await registration.pushManager.getSubscription();

    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });
    }

    const json = subscription.toJSON();

    if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
      return false;
    }

    await savePushSubscription({
      endpoint: json.endpoint,
      keys: {
        p256dh: json.keys.p256dh,
        auth: json.keys.auth,
      },
    });

    return true;
  } catch (error) {
    console.warn("ZUKA persistent Web Push could not be enabled.", error);
    return false;
  }
}

export async function disablePersistentPush(): Promise<void> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;

  try {
    const registration = await navigator.serviceWorker.getRegistration("/");
    const subscription = await registration?.pushManager.getSubscription();
    if (!subscription) return;

    const json = subscription.toJSON();
    if (json.endpoint && json.keys?.p256dh && json.keys?.auth) {
      try {
        await deletePushSubscription({
          endpoint: json.endpoint,
          keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
        });
      } catch (error) {
        console.warn("ZUKA push subscription could not be removed from the server.", error);
      }
    }

    await subscription.unsubscribe();
  } catch (error) {
    console.warn("ZUKA persistent Web Push could not be disabled.", error);
  }
}

function readNotificationPreferences(): {
  browserNotifications?: boolean;
} {
  try {
    const v1 = JSON.parse(localStorage.getItem("zuka_settings_preferences") || "{}") as { browserNotifications?: boolean };
    const v2 = JSON.parse(localStorage.getItem("zuka_settings_preferences_v2") || "{}") as { browserNotifications?: boolean };
    return {
      browserNotifications: v1.browserNotifications !== undefined ? v1.browserNotifications : v2.browserNotifications,
    };
  } catch {
    return {};
  }
}
