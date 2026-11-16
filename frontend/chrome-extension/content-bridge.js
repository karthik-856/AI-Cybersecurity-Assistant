const CHANNEL = "zuka-chrome-sound-bridge-v1";

window.addEventListener("message", (event) => {
  if (event.source !== window || event.origin !== window.location.origin) return;

  const request = event.data;
  if (
    request?.channel !== CHANNEL ||
    request.type !== "request" ||
    typeof request.requestId !== "string" ||
    !["get", "set"].includes(request.action) ||
    (request.action === "set" && typeof request.allowed !== "boolean")
  ) {
    return;
  }

  chrome.runtime.sendMessage(
    { action: request.action, allowed: request.allowed },
    (response) => {
      const runtimeError = chrome.runtime.lastError;
      window.postMessage(
        {
          channel: CHANNEL,
          type: "response",
          requestId: request.requestId,
          ok: !runtimeError && response?.ok === true,
          sound: response?.sound,
        },
        window.location.origin,
      );
    },
  );
});
