/* ZUKA persistent Web Push service worker. */

self.addEventListener("push", (event) => {
  let payload = {};

  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = {
      title: "ZUKA SECURITY ALERT",
      body: event.data ? event.data.text() : "A new security alert requires attention.",
    };
  }

  const title = payload.title || "ZUKA SECURITY ALERT";
  const body = payload.body || "A new security alert requires analyst attention.";

  const options = {
    body,
    icon: "/zuka-push-icon.svg",
    badge: "/zuka-push-badge.svg",
    tag: payload.alert_id ? `zuka-${payload.alert_id}` : "zuka-security-alert",
    renotify: true,
    requireInteraction: payload.severity === "CRITICAL",
    data: {
      url: payload.url || "/alerts",
      alert_id: payload.alert_id || null,
    },
  };

  event.waitUntil(
    self.registration.showNotification(title, options),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const targetUrl = new URL(
    event.notification.data?.url || "/alerts",
    self.location.origin,
  ).href;

  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if ("focus" in client) {
            client.navigate(targetUrl);
            return client.focus();
          }
        }

        if (clients.openWindow) {
          return clients.openWindow(targetUrl);
        }

        return undefined;
      }),
  );
});
