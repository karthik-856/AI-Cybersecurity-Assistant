const CHANNEL = "zuka-chrome-sound-bridge-v1";
const RESPONSE_TIMEOUT_MS = 900;

export type ChromeSiteSound = {
  allowed: boolean;
  setting: "allow" | "block" | "ask";
};

type BridgeResponse = {
  channel: string;
  type: "response";
  requestId: string;
  ok: boolean;
  sound?: ChromeSiteSound;
};

function requestChromeSound(
  action: "get" | "set",
  allowed?: boolean,
): Promise<ChromeSiteSound | null> {
  if (typeof window === "undefined") return Promise.resolve(null);

  return new Promise((resolve) => {
    const requestId = crypto.randomUUID();
    let settled = false;
    const finish = (result: ChromeSiteSound | null) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeout);
      window.removeEventListener("message", onResponse);
      resolve(result);
    };
    const onResponse = (event: MessageEvent<BridgeResponse>) => {
      if (event.source !== window || event.origin !== window.location.origin) return;
      const data = event.data;
      if (data?.channel !== CHANNEL || data.type !== "response" || data.requestId !== requestId) return;
      finish(data.ok && data.sound ? data.sound : null);
    };
    const timeout = window.setTimeout(() => finish(null), RESPONSE_TIMEOUT_MS);

    window.addEventListener("message", onResponse);
    window.postMessage(
      { channel: CHANNEL, type: "request", requestId, action, allowed },
      window.location.origin,
    );
  });
}

export function getChromeSiteSound(): Promise<ChromeSiteSound | null> {
  return requestChromeSound("get");
}

export function setChromeSiteSound(allowed: boolean): Promise<ChromeSiteSound | null> {
  return requestChromeSound("set", allowed);
}
