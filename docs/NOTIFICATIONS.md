# Notifications and hosting availability

The API and PostgreSQL database run on Render/Neon independently of the owner's
laptop. Sleeping or turning off that laptop does not stop those hosted services.

Render Free sleeps after 15 minutes without inbound traffic. Requests wake it,
which can take about a minute. This plan provides no continuous background
processing or always-on availability guarantee. The owner has chosen the free
plan and accepted idle sleep. Keep billing unchanged.

## Enable notifications

1. Sign in as ADMIN or SOC_ANALYST. Open Settings → Alert Notifications.
2. Turn on Browser notifications and allow the browser's permission prompt.
   If previously denied, allow notifications in the site's browser settings.
3. Click Send test notification. Test sound separately and check browser/OS
   volume and Do Not Disturb settings if it is inaudible.
   A successful device test means Chrome accepted the notification API request;
   it cannot prove Windows displayed a banner. If no banner appears, allow
   Chrome in Windows Settings → System → Notifications, and turn off Do Not
   Disturb. The website bounds setup requests so a stalled browser operation
   does not keep the toggle or test button disabled indefinitely.
4. Device notifications can work for newly detected alerts while the page is
   open. Background delivery also needs the server keys below and successful
   registration of that device. The UI distinguishes these states.

Existing alerts are history and do not generate fresh banners at each sign-in.
The included 65-row sample is imported once. With replay disabled and no new
incoming detections, no new security notifications are expected. The test button
verifies delivery without fabricating an alert.

For ongoing demonstration activity, open Network Monitor and choose **Start
demo replay**. It processes one sample every five seconds, up to 65 per run.
**Pause demo replay** stops future samples after the current request. Replay
continues when navigating between signed-in pages in the same tab.
The status and Start/Pause controls are also visible on Dashboard. Refreshing
or signing out ends the run. A sleeping device pauses its browser timers. This
browser-driven demonstration is separate from the hosted API's availability.

A sleeping/offline receiving device cannot be promised immediate notifications.
Push messages request a 24-hour provider TTL for later delivery, subject to the
browser and provider. Another online permitted device can receive pushes
independently of the laptop where its browser supports Web Push.

## Configure Render

Run `python -m scripts.prepare_push_keys` once. It creates
`output/push/render.env`, ignored by Git and Docker, containing:

- `VAPID_PUBLIC_KEY`: the public application-server key.
- `VAPID_PRIVATE_KEY`: the matching secret signing key.
- `VAPID_SUBJECT`: an HTTPS contact URL or mailto contact address.

In Render → zuka-soc → Environment, privately import the file contents using
Add from .env. Keep these keys stable across deploys. Changing them requires
devices to register again. Never paste the private contents into chat, issues,
or committed source. The generator refuses to overwrite an existing file.

After GitHub checks pass, use Manual Deploy → Deploy latest commit. Migrations
add device preferences without deleting existing records. `/api/push/status`
should return `{"configured":true}`. It validates that the keys match.
`/api/push/public-key` returns 503 until valid signing configuration is present.

Enable notifications on each device and send a test. A successful test response
means the push provider accepted it; verify the actual banner before claiming
end-to-end delivery. Real-device delivery is separate from CI's mocked tests.

Only active ADMIN/SOC_ANALYST accounts receive detailed security pushes. Severity
and preview preferences are stored per subscription. Logout unsubscribes that
device; provider responses 404/410 remove expired subscriptions.

References: [Render Free](https://render.com/docs/free),
[Push API](https://developer.mozilla.org/en-US/docs/Web/API/Push_API),
[notification permission](https://developer.mozilla.org/en-US/docs/Web/API/Notifications_API/Using_the_Notifications_API).
