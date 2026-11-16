const ALLOWED_ORIGINS = new Set([
  "http://localhost:5173",
  "http://127.0.0.1:5173",
]);

function readSoundSetting(url, callback) {
  const soundSettings = chrome.contentSettings?.sound;
  if (!soundSettings) {
    callback({ ok: false });
    return;
  }

  soundSettings.get({ primaryUrl: url, secondaryUrl: url }, (details) => {
    if (chrome.runtime.lastError || !details?.setting) {
      callback({ ok: false });
      return;
    }
    callback({
      ok: true,
      sound: {
        setting: details.setting,
        allowed: details.setting === "allow",
      },
    });
  });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  let siteUrl;
  try {
    siteUrl = new URL(sender.url || "");
  } catch {
    sendResponse({ ok: false });
    return false;
  }

  if (!ALLOWED_ORIGINS.has(siteUrl.origin)) {
    sendResponse({ ok: false });
    return false;
  }

  if (message?.action === "get") {
    readSoundSetting(siteUrl.href, sendResponse);
    return true;
  }

  if (message?.action === "set" && typeof message.allowed === "boolean") {
    const soundSettings = chrome.contentSettings?.sound;
    if (!soundSettings) {
      sendResponse({ ok: false });
      return false;
    }

    soundSettings.set(
      {
        primaryPattern: `${siteUrl.origin}/*`,
        setting: message.allowed ? "allow" : "block",
        scope: "regular",
      },
      () => {
        if (chrome.runtime.lastError) {
          sendResponse({ ok: false });
          return;
        }
        readSoundSetting(siteUrl.href, sendResponse);
      },
    );
    return true;
  }

  sendResponse({ ok: false });
  return false;
});
